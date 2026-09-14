#!/usr/bin/env python3
"""Contract test for failed coverglass components, clause 8.8.2 (offline)."""

import copy
import unittest

from e2008_failed_coverglass_components_logic import (
    DEFAULT_STATUS_POLICY,
    POPULATION_STATUS_ASSIGNED,
    POPULATION_STATUS_INCOMPLETE,
    RECOGNISED_FAILURE_MODES,
    REQUIRED_FAILED_COMPONENT_EVIDENCE,
    STATUS_DELIVERABLE_COMPONENT,
    STATUS_FAILED_COMPONENT,
    STATUS_UNDETERMINED,
    assess_component_population,
    component_status,
    deliverable_share_within,
    failed_component_evidence,
    recognised_failure_modes,
    required_failed_component_evidence,
    standing_failure_modes,
    validate_status_policy,
)

OFFERED = ["cg-001", "cg-002", "cg-003", "cg-004"]


def _piece(piece_id="cg-001", modes=None, **overrides):
    piece = {
        "piece_id": piece_id,
        "observed_modes": list(modes or []),
        "inspection_complete": True,
        "segregation_record": "quarantine-shelf-b7",
        "nonconformance_reference": "ncr-2026-0311",
    }
    piece.update(overrides)
    return piece


def _population(pieces=None, **overrides):
    population = {
        "batch_id": "cg-batch-a",
        "offered_piece_ids": list(OFFERED),
        "pieces": pieces if pieces is not None else [_piece(p) for p in OFFERED],
    }
    population.update(overrides)
    return population


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_status_policy(DEFAULT_STATUS_POLICY), DEFAULT_STATUS_POLICY
        )

    def test_default_policy_does_not_admit_retest_clearance(self):
        self.assertFalse(DEFAULT_STATUS_POLICY["admit_retest_clearance"])

    def test_default_policy_does_not_deliver_an_undetermined_piece(self):
        self.assertFalse(DEFAULT_STATUS_POLICY["count_undetermined_as_deliverable"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_status_policy("segregate everything")

    def test_non_boolean_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_STATUS_POLICY)
        broken["require_segregation_record"] = "yes"
        with self.assertRaises(ValueError):
            validate_status_policy(broken)


class VocabularyTests(unittest.TestCase):
    def test_mode_set_comes_back_as_a_tuple_copy(self):
        modes = recognised_failure_modes()
        self.assertEqual(modes, RECOGNISED_FAILURE_MODES)
        self.assertIsInstance(modes, tuple)

    def test_evidence_set_comes_back_as_a_tuple_copy(self):
        evidence = required_failed_component_evidence()
        self.assertEqual(evidence, REQUIRED_FAILED_COMPONENT_EVIDENCE)
        self.assertIsInstance(evidence, tuple)

    def test_measured_and_observed_modes_share_one_vocabulary(self):
        modes = recognised_failure_modes()
        self.assertIn("coverglass-crack", modes)
        self.assertIn("solar-transmittance-degradation-exceeded", modes)


class StandingModeTests(unittest.TestCase):
    def test_an_unmarked_piece_has_nothing_standing(self):
        result = standing_failure_modes(_piece())
        self.assertEqual(result["standing_modes"], [])

    def test_a_repeated_mode_is_read_once(self):
        piece = _piece(modes=["coverglass-crack", "coverglass-crack"])
        self.assertEqual(standing_failure_modes(piece)["observed_modes"], ["coverglass-crack"])

    def test_clearance_is_ignored_when_the_policy_refuses_it(self):
        piece = _piece(
            modes=["coating-blistering"],
            retest_cleared_modes=["coating-blistering"],
            clearance_authority="design-authority",
        )
        result = standing_failure_modes(piece)
        self.assertEqual(result["standing_modes"], ["coating-blistering"])
        self.assertTrue(result["notes"])

    def test_clearance_stands_when_the_policy_admits_it(self):
        policy = copy.deepcopy(DEFAULT_STATUS_POLICY)
        policy["admit_retest_clearance"] = True
        piece = _piece(
            modes=["coating-blistering"],
            retest_cleared_modes=["coating-blistering"],
            clearance_authority="design-authority",
        )
        result = standing_failure_modes(piece, policy)
        self.assertEqual(result["standing_modes"], [])

    def test_clearance_without_an_authority_does_not_stand(self):
        policy = copy.deepcopy(DEFAULT_STATUS_POLICY)
        policy["admit_retest_clearance"] = True
        piece = _piece(
            modes=["coating-blistering"], retest_cleared_modes=["coating-blistering"]
        )
        result = standing_failure_modes(piece, policy)
        self.assertEqual(result["standing_modes"], ["coating-blistering"])

    def test_clearing_a_mode_that_was_never_observed_rejected(self):
        policy = copy.deepcopy(DEFAULT_STATUS_POLICY)
        policy["admit_retest_clearance"] = True
        piece = _piece(modes=["coverglass-crack"], retest_cleared_modes=["chip-beyond-limit"])
        with self.assertRaises(ValueError):
            standing_failure_modes(piece, policy)

    def test_an_unrecognised_mode_rejected(self):
        with self.assertRaises(ValueError):
            standing_failure_modes(_piece(modes=["coverglass-looks-tired"]))

    def test_non_sequence_mode_list_rejected(self):
        with self.assertRaises(ValueError):
            standing_failure_modes(_piece(observed_modes="coverglass-crack"))


class EvidenceTests(unittest.TestCase):
    def test_a_fully_documented_failure_is_missing_nothing(self):
        self.assertEqual(failed_component_evidence(_piece()), [])

    def test_a_missing_segregation_record_is_named(self):
        self.assertEqual(
            failed_component_evidence(_piece(segregation_record="")),
            ["segregation_record"],
        )

    def test_a_missing_nonconformance_reference_is_named(self):
        piece = _piece()
        del piece["nonconformance_reference"]
        self.assertEqual(
            failed_component_evidence(piece), ["nonconformance_reference"]
        )

    def test_evidence_is_not_demanded_when_the_policy_drops_it(self):
        policy = copy.deepcopy(DEFAULT_STATUS_POLICY)
        policy["require_segregation_record"] = False
        policy["require_nonconformance_reference"] = False
        self.assertEqual(
            failed_component_evidence(_piece(segregation_record=""), policy), []
        )


class ComponentStatusTests(unittest.TestCase):
    def test_a_clean_inspected_piece_is_deliverable(self):
        result = component_status(_piece())
        self.assertEqual(result["status"], STATUS_DELIVERABLE_COMPONENT)
        self.assertTrue(result["deliverable"])

    def test_a_single_mode_is_enough_to_fail_the_piece(self):
        result = component_status(_piece(modes=["chip-beyond-limit"]))
        self.assertEqual(result["status"], STATUS_FAILED_COMPONENT)
        self.assertTrue(result["failed"])

    def test_four_modes_give_the_same_status_as_one(self):
        result = component_status(
            _piece(
                modes=[
                    "coverglass-crack",
                    "coating-delamination",
                    "coating-blistering",
                    "chip-beyond-limit",
                ]
            )
        )
        self.assertEqual(result["status"], STATUS_FAILED_COMPONENT)
        self.assertEqual(len(result["standing_modes"]), 4)

    def test_a_failed_piece_is_never_reported_deliverable(self):
        result = component_status(_piece(modes=["coverglass-crack"]))
        self.assertFalse(result["deliverable"])

    def test_an_unfinished_inspection_is_undetermined_not_deliverable(self):
        result = component_status(_piece(inspection_complete=False))
        self.assertEqual(result["status"], STATUS_UNDETERMINED)
        self.assertFalse(result["deliverable"])

    def test_a_mode_outranks_an_unfinished_inspection(self):
        result = component_status(
            _piece(modes=["coverglass-crack"], inspection_complete=False)
        )
        self.assertEqual(result["status"], STATUS_FAILED_COMPONENT)

    def test_a_failed_piece_without_segregation_is_not_complete(self):
        result = component_status(_piece(modes=["coverglass-crack"], segregation_record=""))
        self.assertFalse(result["status_complete"])
        self.assertEqual(result["missing_evidence"], ["segregation_record"])

    def test_a_documented_failure_is_complete(self):
        result = component_status(_piece(modes=["coverglass-crack"]))
        self.assertTrue(result["status_complete"])

    def test_a_non_boolean_inspection_flag_rejected(self):
        with self.assertRaises(ValueError):
            component_status(_piece(inspection_complete="done"))

    def test_a_piece_without_an_identifier_rejected(self):
        piece = _piece()
        del piece["piece_id"]
        with self.assertRaises(ValueError):
            component_status(piece)

    def test_findings_name_the_piece_and_the_mode(self):
        result = component_status(_piece("cg-077", modes=["coating-delamination"]))
        joined = " ".join(result["findings"])
        self.assertIn("cg-077", joined)
        self.assertIn("coating-delamination", joined)


class PopulationTests(unittest.TestCase):
    def test_a_fully_statused_clean_batch_settles(self):
        result = assess_component_population(_population())
        self.assertEqual(result["verdict"], POPULATION_STATUS_ASSIGNED)
        self.assertEqual(result["deliverable_count"], 4)
        self.assertEqual(result["failed_piece_ids"], [])

    def test_a_failed_piece_leaves_the_deliverable_count(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[1]["observed_modes"] = ["coverglass-crack"]
        result = assess_component_population(_population(pieces))
        self.assertEqual(result["failed_piece_ids"], ["cg-002"])
        self.assertNotIn("cg-002", result["deliverable_piece_ids"])
        self.assertEqual(result["deliverable_count"], 3)

    def test_the_failed_share_is_reported(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[1]["observed_modes"] = ["coverglass-crack"]
        result = assess_component_population(_population(pieces))
        self.assertAlmostEqual(result["failed_fraction"], 0.25, places=9)

    def test_a_documented_failure_still_settles_the_population(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[1]["observed_modes"] = ["coverglass-crack"]
        result = assess_component_population(_population(pieces))
        self.assertEqual(result["verdict"], POPULATION_STATUS_ASSIGNED)

    def test_an_undocumented_failure_leaves_the_population_incomplete(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[1]["observed_modes"] = ["coverglass-crack"]
        pieces[1]["nonconformance_reference"] = ""
        result = assess_component_population(_population(pieces))
        self.assertEqual(result["verdict"], POPULATION_STATUS_INCOMPLETE)
        self.assertEqual(result["incomplete_evidence_piece_ids"], ["cg-002"])

    def test_an_offered_piece_with_no_record_is_undetermined(self):
        pieces = [_piece(p) for p in OFFERED[:3]]
        result = assess_component_population(_population(pieces))
        self.assertEqual(result["undetermined_piece_ids"], ["cg-004"])
        self.assertEqual(result["verdict"], POPULATION_STATUS_INCOMPLETE)

    def test_an_undetermined_piece_is_not_delivered_by_default(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[3]["inspection_complete"] = False
        result = assess_component_population(_population(pieces))
        self.assertNotIn("cg-004", result["deliverable_piece_ids"])

    def test_a_policy_may_carry_undetermined_pieces_into_the_delivery(self):
        policy = copy.deepcopy(DEFAULT_STATUS_POLICY)
        policy["count_undetermined_as_deliverable"] = True
        pieces = [_piece(p) for p in OFFERED]
        pieces[3]["inspection_complete"] = False
        result = assess_component_population(_population(pieces), policy)
        self.assertIn("cg-004", result["deliverable_piece_ids"])
        self.assertEqual(result["verdict"], POPULATION_STATUS_ASSIGNED)

    def test_a_record_for_a_piece_the_batch_does_not_offer_is_named(self):
        pieces = [_piece(p) for p in OFFERED] + [_piece("cg-999")]
        result = assess_component_population(_population(pieces))
        self.assertEqual(result["foreign_piece_ids"], ["cg-999"])
        self.assertEqual(result["verdict"], POPULATION_STATUS_INCOMPLETE)

    def test_statuses_are_grouped(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[0]["observed_modes"] = ["coating-blistering"]
        result = assess_component_population(_population(pieces))
        self.assertEqual(
            result["grouped_by_status"][STATUS_FAILED_COMPONENT], ["cg-001"]
        )

    def test_statuses_come_back_in_identifier_order(self):
        pieces = [_piece(p) for p in reversed(OFFERED)]
        result = assess_component_population(_population(pieces))
        ids = [entry["piece_id"] for entry in result["piece_statuses"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_piece_identifier_rejected(self):
        pieces = [_piece("cg-001"), _piece("cg-001")]
        with self.assertRaises(ValueError):
            assess_component_population(_population(pieces))

    def test_an_empty_piece_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_population(_population([]))

    def test_a_population_without_a_batch_identifier_rejected(self):
        population = _population()
        del population["batch_id"]
        with self.assertRaises(ValueError):
            assess_component_population(population)

    def test_non_mapping_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_population([_piece()])


class ShareTests(unittest.TestCase):
    def test_a_share_under_the_allowance_stands(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[0]["observed_modes"] = ["coverglass-crack"]
        result = assess_component_population(_population(pieces))
        self.assertTrue(deliverable_share_within(result, 0.5))

    def test_a_share_landing_on_the_allowance_is_admissible(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[0]["observed_modes"] = ["coverglass-crack"]
        result = assess_component_population(_population(pieces))
        self.assertTrue(deliverable_share_within(result, 0.25))

    def test_a_share_past_the_allowance_does_not_stand(self):
        pieces = [_piece(p) for p in OFFERED]
        pieces[0]["observed_modes"] = ["coverglass-crack"]
        pieces[1]["observed_modes"] = ["chip-beyond-limit"]
        result = assess_component_population(_population(pieces))
        self.assertFalse(deliverable_share_within(result, 0.25))

    def test_an_allowance_above_one_rejected(self):
        result = assess_component_population(_population())
        with self.assertRaises(ValueError):
            deliverable_share_within(result, 1.5)

    def test_a_result_without_a_share_rejected(self):
        with self.assertRaises(ValueError):
            deliverable_share_within({}, 0.1)


if __name__ == "__main__":
    unittest.main()
