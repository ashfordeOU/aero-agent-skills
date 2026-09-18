#!/usr/bin/env python3
"""Contract tests for the Annex A nonconformance report data item.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused data-item
policy, a report never raised, one with no identifier, a board stage
reached with no disposition proposed, a stage block left unfilled, a
disposition path block missing, a customer route closed with no customer
approval, and the two board routings the content derives.
"""

import unittest

from q1009_ncr_drd_logic import (
    ACCEPTANCE_TECHNICAL_JUSTIFICATION,
    AFFECTED_ITEM_AND_CONFIGURATION,
    BASE_CONTENT_INCOMPLETE,
    BOARD_BLOCKS,
    BOARD_CUSTOMER,
    BOARD_INTERNAL,
    CATEGORY_MAJOR,
    CATEGORY_MINOR,
    CAUSE_ANALYSIS,
    CLOSURE_BLOCKS,
    COMPLETE_FOR_CLOSURE,
    CUSTOMER_APPROVAL_MISSING,
    CUSTOMER_APPROVAL_RECORD,
    DEFAULT_NCR_DRD_POLICY,
    DISPOSITION_NOT_PROPOSED,
    DISPOSITION_PATH_BLOCKS,
    DISPOSITION_REPAIR,
    DISPOSITION_REWORK,
    DISPOSITION_SCRAP,
    DISPOSITION_USE_AS_IS,
    EFFECT_ON_INTERFACES_AND_LIFETIME,
    NCR_NOT_RAISED,
    PATH_CONTENT_MISSING,
    RAISING_BLOCKS,
    READY_FOR_CUSTOMER_BOARD,
    READY_FOR_INTERNAL_BOARD,
    REINSPECTION_AND_RETEST_RECORD,
    REWORK_PROCEDURE_REFERENCE,
    STAGE_AT_BOARD,
    STAGE_AT_CLOSURE,
    STAGE_AT_RAISING,
    REQUIREMENT_NOT_MET,
    assess_nonconformance_report_drd,
    base_blocks_for_stage,
    base_content_coverage,
    block_is_filled,
    board_required,
    content_coverage,
    customer_blocks_for,
    missing_blocks,
    path_blocks_for,
    required_blocks,
    validate_block_record,
    validate_blocks,
    validate_ncr_drd_policy,
    validate_report_identity,
)


def _policy(**overrides):
    policy = dict(DEFAULT_NCR_DRD_POLICY)
    policy.update(overrides)
    return policy


def _identity(**overrides):
    identity = {
        "ncr_identifier": "NCR-2204",
        "affected_item": "bracket-assembly-77",
        "stage": STAGE_AT_BOARD,
        "category": CATEGORY_MINOR,
        "safety_effect": False,
        "proposed_disposition": DISPOSITION_REWORK,
    }
    identity.update(overrides)
    return identity


def _blocks_for(names, unfilled=(), absent=()):
    records = []
    for index, name in enumerate(names):
        if name in absent:
            continue
        records.append(
            {
                "block": name,
                "present": name not in unfilled,
                "entry_reference": "" if name in unfilled else "NCR-ENTRY-%02d" % index,
            }
        )
    return records


def _report(stage=STAGE_AT_BOARD, disposition=DISPOSITION_REWORK, **overrides):
    identity = _identity(stage=stage, proposed_disposition=disposition)
    names = list(base_blocks_for_stage(stage))
    if stage in (STAGE_AT_BOARD, STAGE_AT_CLOSURE) and disposition is not None:
        names.extend(path_blocks_for(disposition))
    names.extend(customer_blocks_for(validate_report_identity(identity)))
    report = dict(identity)
    report["content_blocks"] = _blocks_for(names)
    report.update(overrides)
    return report


def _case(**overrides):
    case = {"policy": _policy(), "report": _report()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_ncr_drd_policy(DEFAULT_NCR_DRD_POLICY), DEFAULT_NCR_DRD_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_ncr_drd_policy("customer")

    def test_a_policy_with_no_customer_route_refused(self):
        with self.assertRaises(ValueError):
            validate_ncr_drd_policy(
                _policy(
                    customer_board_on_major=False,
                    customer_board_on_safety_effect=False,
                )
            )

    def test_non_boolean_approval_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_ncr_drd_policy(_policy(require_customer_approval_record="yes"))


class IdentityValidationTests(unittest.TestCase):
    def test_identity_is_read_back(self):
        identity = validate_report_identity(_identity())
        self.assertEqual(identity["ncr_identifier"], "NCR-2204")
        self.assertEqual(identity["stage"], STAGE_AT_BOARD)

    def test_unrecognised_stage_refused(self):
        with self.assertRaises(ValueError):
            validate_report_identity(_identity(stage="nearly-closed"))

    def test_unrecognised_category_refused(self):
        with self.assertRaises(ValueError):
            validate_report_identity(_identity(category="quite-bad"))

    def test_unrecognised_disposition_refused(self):
        with self.assertRaises(ValueError):
            validate_report_identity(_identity(proposed_disposition="leave-it"))

    def test_non_boolean_safety_effect_refused(self):
        with self.assertRaises(ValueError):
            validate_report_identity(_identity(safety_effect="maybe"))


class BlockValidationTests(unittest.TestCase):
    def test_unrecognised_block_refused(self):
        with self.assertRaises(ValueError):
            validate_block_record(
                {"block": "extra-thoughts", "present": True, "entry_reference": "X"}
            )

    def test_duplicate_block_refused(self):
        record = {
            "block": CAUSE_ANALYSIS,
            "present": True,
            "entry_reference": "NCR-ENTRY-01",
        }
        with self.assertRaises(ValueError):
            validate_blocks([record, dict(record)])

    def test_a_present_block_with_no_reference_is_not_filled(self):
        self.assertFalse(
            block_is_filled(
                {"block": CAUSE_ANALYSIS, "present": True, "entry_reference": "  "}
            )
        )

    def test_a_referenced_present_block_is_filled(self):
        self.assertTrue(
            block_is_filled(
                {"block": CAUSE_ANALYSIS, "present": True, "entry_reference": "CA-9"}
            )
        )


class StageAndPathTests(unittest.TestCase):
    def test_raising_owes_only_the_raising_blocks(self):
        self.assertEqual(base_blocks_for_stage(STAGE_AT_RAISING), RAISING_BLOCKS)

    def test_the_board_stage_adds_the_board_blocks(self):
        owed = base_blocks_for_stage(STAGE_AT_BOARD)
        self.assertEqual(owed, RAISING_BLOCKS + BOARD_BLOCKS)

    def test_closure_adds_the_closure_blocks(self):
        owed = base_blocks_for_stage(STAGE_AT_CLOSURE)
        self.assertEqual(owed, RAISING_BLOCKS + BOARD_BLOCKS + CLOSURE_BLOCKS)

    def test_each_disposition_path_brings_its_own_blocks(self):
        self.assertIn(
            ACCEPTANCE_TECHNICAL_JUSTIFICATION, path_blocks_for(DISPOSITION_USE_AS_IS)
        )
        self.assertIn(REWORK_PROCEDURE_REFERENCE, path_blocks_for(DISPOSITION_REWORK))
        self.assertEqual(len(path_blocks_for(DISPOSITION_SCRAP)), 1)

    def test_no_disposition_brings_no_path_blocks(self):
        self.assertEqual(path_blocks_for(None), ())

    def test_required_blocks_do_not_repeat_a_shared_path_block(self):
        identity = validate_report_identity(
            _identity(proposed_disposition=DISPOSITION_REPAIR)
        )
        owed = required_blocks(identity)
        self.assertEqual(
            owed.count(EFFECT_ON_INTERFACES_AND_LIFETIME), 1
        )


class BoardRoutingTests(unittest.TestCase):
    def test_a_minor_rework_settles_internally(self):
        identity = validate_report_identity(_identity())
        self.assertEqual(board_required(identity), BOARD_INTERNAL)

    def test_a_major_nonconformance_goes_to_the_customer_board(self):
        identity = validate_report_identity(_identity(category=CATEGORY_MAJOR))
        self.assertEqual(board_required(identity), BOARD_CUSTOMER)

    def test_a_safety_effect_goes_to_the_customer_board(self):
        identity = validate_report_identity(_identity(safety_effect=True))
        self.assertEqual(board_required(identity), BOARD_CUSTOMER)

    def test_use_as_is_goes_to_the_customer_board_on_its_own(self):
        identity = validate_report_identity(
            _identity(proposed_disposition=DISPOSITION_USE_AS_IS)
        )
        self.assertEqual(board_required(identity), BOARD_CUSTOMER)

    def test_the_customer_approval_block_is_owed_only_at_closure(self):
        at_board = validate_report_identity(_identity(category=CATEGORY_MAJOR))
        at_closure = validate_report_identity(
            _identity(category=CATEGORY_MAJOR, stage=STAGE_AT_CLOSURE)
        )
        self.assertEqual(customer_blocks_for(at_board), ())
        self.assertEqual(
            customer_blocks_for(at_closure), (CUSTOMER_APPROVAL_RECORD,)
        )


class CoverageTests(unittest.TestCase):
    def test_a_complete_report_covers_every_owed_block(self):
        identity = validate_report_identity(_identity())
        blocks = _report()["content_blocks"]
        self.assertAlmostEqual(content_coverage(blocks, identity), 1.0, places=9)

    def test_an_unfilled_block_is_missing(self):
        blocks = _blocks_for(
            base_blocks_for_stage(STAGE_AT_RAISING), unfilled=(REQUIREMENT_NOT_MET,)
        )
        self.assertEqual(
            missing_blocks(blocks, (REQUIREMENT_NOT_MET,)), (REQUIREMENT_NOT_MET,)
        )

    def test_an_absent_block_is_missing(self):
        blocks = _blocks_for(
            base_blocks_for_stage(STAGE_AT_RAISING),
            absent=(AFFECTED_ITEM_AND_CONFIGURATION,),
        )
        self.assertEqual(
            missing_blocks(blocks, (AFFECTED_ITEM_AND_CONFIGURATION,)),
            (AFFECTED_ITEM_AND_CONFIGURATION,),
        )

    def test_base_coverage_ignores_the_path_blocks(self):
        identity = validate_report_identity(_identity())
        blocks = [
            block
            for block in _report()["content_blocks"]
            if block["block"] != REINSPECTION_AND_RETEST_RECORD
        ]
        self.assertAlmostEqual(base_content_coverage(blocks, identity), 1.0, places=9)
        self.assertLess(content_coverage(blocks, identity), 1.0)

    def test_a_relaxed_policy_tolerates_a_missing_stage_block(self):
        report = _report()
        report["content_blocks"] = [
            block
            for block in report["content_blocks"]
            if block["block"] != CAUSE_ANALYSIS
        ]
        result = assess_nonconformance_report_drd(
            _case(policy=_policy(min_block_coverage=0.8), report=report)
        )
        self.assertEqual(result["verdict"], READY_FOR_INTERNAL_BOARD)
        self.assertEqual(len(result["advisories"]), 1)

    def test_coverage_falls_with_a_missing_block(self):
        identity = validate_report_identity(_identity(stage=STAGE_AT_RAISING))
        blocks = _blocks_for(
            base_blocks_for_stage(STAGE_AT_RAISING),
            absent=(AFFECTED_ITEM_AND_CONFIGURATION,),
        )
        self.assertAlmostEqual(content_coverage(blocks, identity), 0.8, places=9)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_board_report_is_ready_for_the_internal_board(self):
        result = assess_nonconformance_report_drd(_case())
        self.assertEqual(result["verdict"], READY_FOR_INTERNAL_BOARD)
        self.assertAlmostEqual(result["content_coverage"], 1.0, places=9)

    def test_no_report_at_all_stops_the_assessment(self):
        result = assess_nonconformance_report_drd(_case(report=None))
        self.assertEqual(result["verdict"], NCR_NOT_RAISED)

    def test_a_report_with_no_identifier_is_not_raised(self):
        report = _report()
        report["ncr_identifier"] = "  "
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], NCR_NOT_RAISED)

    def test_the_board_stage_without_a_disposition_stops_there(self):
        report = _report(disposition=None)
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], DISPOSITION_NOT_PROPOSED)

    def test_a_missing_stage_block_outranks_the_path_check(self):
        report = _report()
        report["content_blocks"] = [
            block
            for block in report["content_blocks"]
            if block["block"] != CAUSE_ANALYSIS
        ]
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], BASE_CONTENT_INCOMPLETE)

    def test_a_missing_path_block_is_reported_against_its_disposition(self):
        report = _report()
        report["content_blocks"] = [
            block
            for block in report["content_blocks"]
            if block["block"] != REINSPECTION_AND_RETEST_RECORD
        ]
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], PATH_CONTENT_MISSING)
        self.assertEqual(
            result["missing_path_blocks"], (REINSPECTION_AND_RETEST_RECORD,)
        )

    def test_a_use_as_is_report_is_ready_for_the_customer_board(self):
        report = _report(disposition=DISPOSITION_USE_AS_IS)
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], READY_FOR_CUSTOMER_BOARD)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_closed_customer_route_without_approval_is_caught(self):
        report = _report(stage=STAGE_AT_CLOSURE, disposition=DISPOSITION_USE_AS_IS)
        report["content_blocks"] = [
            block
            for block in report["content_blocks"]
            if block["block"] != CUSTOMER_APPROVAL_RECORD
        ]
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], CUSTOMER_APPROVAL_MISSING)

    def test_a_closed_customer_route_with_approval_is_complete(self):
        report = _report(stage=STAGE_AT_CLOSURE, disposition=DISPOSITION_USE_AS_IS)
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], COMPLETE_FOR_CLOSURE)

    def test_a_closed_internal_route_needs_no_customer_approval(self):
        report = _report(stage=STAGE_AT_CLOSURE, disposition=DISPOSITION_REWORK)
        result = assess_nonconformance_report_drd(_case(report=report))
        self.assertEqual(result["verdict"], COMPLETE_FOR_CLOSURE)
        self.assertEqual(result["board"], BOARD_INTERNAL)

    def test_a_report_with_no_content_blocks_key_is_refused(self):
        report = _report()
        del report["content_blocks"]
        with self.assertRaises(ValueError):
            assess_nonconformance_report_drd(_case(report=report))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_nonconformance_report_drd(("report",))


if __name__ == "__main__":
    unittest.main()
