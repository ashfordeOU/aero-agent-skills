#!/usr/bin/env python3
"""Contract tests for the Annex D parts approval document data item.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused data-item
policy, a submission that never arrived, one with no reference or issue,
a required block absent, a block pointing at nothing, evidence weighed
against a risk index it cannot meet, a shortfall with no mitigation
behind it, and a shortfall a mitigation can close.
"""

import unittest

from q6013_parts_approval_document_drd_logic import (
    APPROVAL_RECOMMENDED,
    APPROVAL_RECOMMENDED_WITH_CONDITIONS,
    CONTENT_COVERAGE_SHORT,
    CRITICALITY_HOUSEKEEPING,
    CRITICALITY_MISSION_CRITICAL,
    CRITICALITY_SINGLE_STRING_PAYLOAD,
    DEFAULT_APPROVAL_DRD_POLICY,
    DOCUMENT_NOT_SUBMITTED,
    ENVIRONMENT_BENIGN,
    ENVIRONMENT_DEEP_SPACE,
    ENVIRONMENT_GEOSTATIONARY,
    EVALUATION_AND_TEST_EVIDENCE,
    EVIDENCE_BEARING_BLOCKS,
    EVIDENCE_INSUFFICIENT_FOR_RISK,
    MITIGATION_AND_CONTROLS,
    MITIGATION_NOT_PROPOSED,
    PROCUREMENT_AND_TRACEABILITY_PLAN,
    RADIATION_EVIDENCE,
    RELIABILITY_AND_FAILURE_RATE_BASIS,
    REQUIRED_CONTENT_BLOCKS,
    RISK_ASSESSMENT,
    absent_blocks,
    assess_parts_approval_document_drd,
    block_index,
    block_is_supported,
    content_coverage,
    evidence_shortfall,
    evidence_strength,
    mitigation_is_proposed,
    required_evidence_strength,
    risk_index,
    unsupported_blocks,
    validate_approval_drd_policy,
    validate_block_record,
    validate_blocks,
    validate_submission_identity,
)


def _policy(**overrides):
    policy = dict(DEFAULT_APPROVAL_DRD_POLICY)
    policy.update(overrides)
    return policy


def _blocks(present=None, references=None, strengths=None, drop=()):
    present_map = present or {}
    reference_map = references or {}
    strength_map = strengths or {}
    default_strengths = {
        EVALUATION_AND_TEST_EVIDENCE: 0.9,
        RADIATION_EVIDENCE: 0.85,
        RELIABILITY_AND_FAILURE_RATE_BASIS: 0.8,
        RISK_ASSESSMENT: 0.8,
        MITIGATION_AND_CONTROLS: 0.7,
    }
    records = []
    for index, name in enumerate(REQUIRED_CONTENT_BLOCKS):
        if name in drop:
            continue
        records.append(
            {
                "block": name,
                "present": present_map.get(name, True),
                "evidence_reference": reference_map.get(
                    name, "PAD-EV-%02d" % (index + 1)
                ),
                "strength": strength_map.get(
                    name, default_strengths.get(name, 0.0)
                ),
            }
        )
    return records


def _evidence_at(level, mitigation=0.7):
    strengths = {name: level for name in EVIDENCE_BEARING_BLOCKS}
    strengths[MITIGATION_AND_CONTROLS] = mitigation
    return _blocks(strengths=strengths)


def _submission(**overrides):
    submission = {
        "document_reference": "PAD-COTS-5501",
        "issue": "issue 1",
        "part_identifier": "MCU-3380",
        "application_criticality": CRITICALITY_SINGLE_STRING_PAYLOAD,
        "operating_environment": ENVIRONMENT_GEOSTATIONARY,
        "content_blocks": _blocks(),
    }
    submission.update(overrides)
    return submission


def _case(**overrides):
    case = {"policy": _policy(), "submission": _submission()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_approval_drd_policy(DEFAULT_APPROVAL_DRD_POLICY),
            DEFAULT_APPROVAL_DRD_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_approval_drd_policy(0.45)

    def test_base_plus_span_above_complete_refused(self):
        with self.assertRaises(ValueError):
            validate_approval_drd_policy(
                _policy(base_required_evidence=0.8, risk_evidence_span=0.5)
            )

    def test_negative_shortfall_allowance_refused(self):
        with self.assertRaises(ValueError):
            validate_approval_drd_policy(_policy(conditional_shortfall_allowance=-0.1))

    def test_non_boolean_mitigation_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_approval_drd_policy(_policy(require_mitigation_when_short="yes"))


class IdentityValidationTests(unittest.TestCase):
    def test_identity_is_read_back(self):
        identity = validate_submission_identity(_submission())
        self.assertEqual(identity["document_reference"], "PAD-COTS-5501")
        self.assertEqual(identity["part_identifier"], "MCU-3380")

    def test_unrecognised_criticality_refused(self):
        with self.assertRaises(ValueError):
            validate_submission_identity(
                _submission(application_criticality="quite-important")
            )

    def test_unrecognised_environment_refused(self):
        with self.assertRaises(ValueError):
            validate_submission_identity(
                _submission(operating_environment="somewhere-cold")
            )

    def test_non_mapping_submission_refused(self):
        with self.assertRaises(ValueError):
            validate_submission_identity("PAD-COTS-5501")


class BlockValidationTests(unittest.TestCase):
    def test_unrecognised_block_refused(self):
        with self.assertRaises(ValueError):
            validate_block_record({"block": "cover-letter", "present": True})

    def test_duplicate_block_refused(self):
        blocks = _blocks()
        blocks.append(dict(blocks[0]))
        with self.assertRaises(ValueError):
            validate_blocks(blocks)

    def test_strength_outside_zero_to_one_refused(self):
        with self.assertRaises(ValueError):
            validate_block_record(
                {
                    "block": RADIATION_EVIDENCE,
                    "present": True,
                    "evidence_reference": "PAD-EV-05",
                    "strength": 1.4,
                }
            )

    def test_block_with_no_reference_is_unsupported(self):
        record = validate_block_record(
            {
                "block": PROCUREMENT_AND_TRACEABILITY_PLAN,
                "present": True,
                "evidence_reference": "   ",
            }
        )
        self.assertFalse(block_is_supported(record))

    def test_block_index_maps_every_declared_block(self):
        self.assertEqual(len(block_index(_blocks())), len(REQUIRED_CONTENT_BLOCKS))


class CoverageTests(unittest.TestCase):
    def test_full_submission_covers_every_block(self):
        self.assertAlmostEqual(content_coverage(_blocks()), 1.0, places=9)

    def test_absent_block_is_named_and_lowers_coverage(self):
        blocks = _blocks(drop=(RISK_ASSESSMENT,))
        self.assertEqual(absent_blocks(blocks), (RISK_ASSESSMENT,))
        self.assertAlmostEqual(
            content_coverage(blocks),
            (len(REQUIRED_CONTENT_BLOCKS) - 1) / float(len(REQUIRED_CONTENT_BLOCKS)),
            places=9,
        )

    def test_block_pointing_at_nothing_is_named(self):
        blocks = _blocks(references={RADIATION_EVIDENCE: ""})
        self.assertEqual(unsupported_blocks(blocks), (RADIATION_EVIDENCE,))


class RiskTests(unittest.TestCase):
    def test_risk_index_multiplies_the_two_weights(self):
        identity = validate_submission_identity(_submission())
        self.assertAlmostEqual(risk_index(identity), 0.64, places=9)

    def test_benign_housekeeping_carries_the_lowest_risk(self):
        identity = validate_submission_identity(
            _submission(
                application_criticality=CRITICALITY_HOUSEKEEPING,
                operating_environment=ENVIRONMENT_BENIGN,
            )
        )
        self.assertAlmostEqual(risk_index(identity), 0.16, places=9)

    def test_critical_deep_space_carries_the_highest_risk(self):
        identity = validate_submission_identity(
            _submission(
                application_criticality=CRITICALITY_MISSION_CRITICAL,
                operating_environment=ENVIRONMENT_DEEP_SPACE,
            )
        )
        self.assertAlmostEqual(risk_index(identity), 1.0, places=9)

    def test_required_evidence_rises_with_the_risk(self):
        identity = validate_submission_identity(_submission())
        self.assertAlmostEqual(
            required_evidence_strength(identity, _policy()), 0.77, places=9
        )

    def test_the_bar_is_lower_for_a_benign_application(self):
        identity = validate_submission_identity(
            _submission(
                application_criticality=CRITICALITY_HOUSEKEEPING,
                operating_environment=ENVIRONMENT_BENIGN,
            )
        )
        self.assertAlmostEqual(
            required_evidence_strength(identity, _policy()), 0.53, places=9
        )


class EvidenceTests(unittest.TestCase):
    def test_evidence_strength_is_the_weighted_mean(self):
        self.assertAlmostEqual(evidence_strength(_blocks()), 0.85, places=9)

    def test_a_uniform_level_reads_back_as_that_level(self):
        self.assertAlmostEqual(evidence_strength(_evidence_at(0.7)), 0.7, places=9)

    def test_an_unreferenced_evidence_block_contributes_nothing(self):
        blocks = _blocks(references={RADIATION_EVIDENCE: ""})
        self.assertAlmostEqual(
            evidence_strength(blocks), (2.7 + 1.6 + 0.8) / 9.0, places=9
        )

    def test_evidence_above_the_bar_has_no_shortfall(self):
        identity = validate_submission_identity(_submission())
        self.assertAlmostEqual(
            evidence_shortfall(_blocks(), identity, _policy()), 0.0, places=9
        )

    def test_evidence_below_the_bar_reports_the_gap(self):
        identity = validate_submission_identity(_submission())
        self.assertAlmostEqual(
            evidence_shortfall(_evidence_at(0.7), identity, _policy()),
            0.07,
            places=9,
        )

    def test_mitigation_with_no_strength_is_not_proposed(self):
        self.assertFalse(mitigation_is_proposed(_evidence_at(0.7, mitigation=0.0)))

    def test_mitigation_with_strength_is_proposed(self):
        self.assertTrue(mitigation_is_proposed(_evidence_at(0.7)))


class AssessmentTests(unittest.TestCase):
    def test_strong_submission_earns_a_recommendation(self):
        result = assess_parts_approval_document_drd(_case())
        self.assertEqual(result["verdict"], APPROVAL_RECOMMENDED)
        self.assertAlmostEqual(result["evidence_strength"], 0.85, places=9)

    def test_absent_submission_stops_the_assessment(self):
        result = assess_parts_approval_document_drd(_case(submission=None))
        self.assertEqual(result["verdict"], DOCUMENT_NOT_SUBMITTED)

    def test_blank_issue_stops_the_assessment(self):
        result = assess_parts_approval_document_drd(
            _case(submission=_submission(issue="  "))
        )
        self.assertEqual(result["verdict"], DOCUMENT_NOT_SUBMITTED)

    def test_short_coverage_outranks_the_later_checks(self):
        submission = _submission(content_blocks=_blocks(drop=(RISK_ASSESSMENT,)))
        result = assess_parts_approval_document_drd(_case(submission=submission))
        self.assertEqual(result["verdict"], CONTENT_COVERAGE_SHORT)

    def test_weak_evidence_for_a_high_risk_is_refused(self):
        submission = _submission(content_blocks=_evidence_at(0.4))
        result = assess_parts_approval_document_drd(_case(submission=submission))
        self.assertEqual(result["verdict"], EVIDENCE_INSUFFICIENT_FOR_RISK)

    def test_a_closeable_shortfall_with_no_mitigation_is_reported(self):
        submission = _submission(content_blocks=_evidence_at(0.7, mitigation=0.0))
        result = assess_parts_approval_document_drd(_case(submission=submission))
        self.assertEqual(result["verdict"], MITIGATION_NOT_PROPOSED)

    def test_a_closeable_shortfall_with_mitigation_is_conditional(self):
        submission = _submission(content_blocks=_evidence_at(0.7))
        result = assess_parts_approval_document_drd(_case(submission=submission))
        self.assertEqual(result["verdict"], APPROVAL_RECOMMENDED_WITH_CONDITIONS)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_shortfall_landing_on_the_allowance_is_still_conditional(self):
        submission = _submission(content_blocks=_evidence_at(0.62))
        result = assess_parts_approval_document_drd(_case(submission=submission))
        self.assertEqual(result["verdict"], APPROVAL_RECOMMENDED_WITH_CONDITIONS)
        self.assertAlmostEqual(result["evidence_shortfall"], 0.15, places=9)

    def test_the_same_evidence_passes_at_a_lower_risk(self):
        submission = _submission(
            application_criticality=CRITICALITY_HOUSEKEEPING,
            operating_environment=ENVIRONMENT_BENIGN,
            content_blocks=_evidence_at(0.7),
        )
        result = assess_parts_approval_document_drd(_case(submission=submission))
        self.assertEqual(result["verdict"], APPROVAL_RECOMMENDED)

    def test_submission_with_no_content_blocks_refused(self):
        submission = _submission()
        del submission["content_blocks"]
        with self.assertRaises(ValueError):
            assess_parts_approval_document_drd(_case(submission=submission))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_approval_document_drd(("submission",))


if __name__ == "__main__":
    unittest.main()
