"""Contract test for the ECSS-Q-ST-60-05C clause 7.3.3 likeness-approval leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_approval_by_design_similarity.py
"""

import unittest

from q6005_approval_by_design_similarity_logic import (
    ATTRIBUTE_CRITICALITY,
    BASE_DELTA_SAMPLE,
    DIVERGENCE_RANKS,
    INDEX_TOLERANCE,
    MAX_MAJOR_VARIANT_ATTRIBUTES,
    REFERENCE_VALIDITY_MONTHS,
    ROUTE_FULL,
    ROUTE_FULL_CREDIT,
    ROUTE_PARTIAL,
    SAMPLE_PER_MAJOR_VARIANT,
    assess_similarity,
    attribute_weight,
    blocking_findings,
    decisive_attributes,
    delta_sample_size,
    delta_test_groups,
    divergence_index,
    divergence_rank,
    governing_attribute,
    normalize_dossier,
    quality_demand,
    rank_candidates,
)


def attributes(**overrides):
    """Every decisive attribute identical, perturbed by the caller."""
    base = {a: "identical" for a in decisive_attributes()}
    base.update(overrides)
    return base


def dossier(**overrides):
    """A candidate whose reference is live, same-line and equally demanding."""
    base = {
        "candidate_id": "hyb-cand-01",
        "reference_id": "hyb-ref-01",
        "reference_approved": True,
        "reference_approval_age_months": 6.0,
        "candidate_quality_level": "level-2",
        "reference_quality_level": "level-2",
        "attributes": attributes(),
    }
    base.update(overrides)
    return base


class AttributeWeightTests(unittest.TestCase):
    def test_every_known_attribute_carries_a_positive_weight(self):
        for attribute in ATTRIBUTE_CRITICALITY:
            self.assertGreater(attribute_weight(attribute), 0.0)

    def test_a_decisive_attribute_outweighs_a_supporting_one(self):
        self.assertGreater(
            attribute_weight("sealing-method"), attribute_weight("design-rule-set")
        )

    def test_unknown_attribute_rejected(self):
        with self.assertRaises(ValueError):
            attribute_weight("paint-colour")

    def test_the_manufacturing_line_is_decisive(self):
        self.assertIn("manufacturing-line", decisive_attributes())


class DivergenceRankTests(unittest.TestCase):
    def test_identical_is_the_lowest_rank(self):
        self.assertEqual(divergence_rank("identical"), 0)

    def test_incompatible_is_the_highest_rank(self):
        self.assertEqual(divergence_rank("incompatible"), max(DIVERGENCE_RANKS.values()))

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            divergence_rank("roughly-the-same")


class QualityDemandTests(unittest.TestCase):
    def test_level_one_is_the_most_demanding(self):
        self.assertGreater(quality_demand("level-1"), quality_demand("level-3"))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            quality_demand("level-0")


class NormalizeDossierTests(unittest.TestCase):
    def test_a_complete_dossier_round_trips(self):
        record = normalize_dossier(dossier())
        self.assertEqual(record["candidate_id"], "hyb-cand-01")
        self.assertAlmostEqual(record["reference_approval_age_months"], 6.0)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dossier(["hyb-cand-01"])

    def test_blank_candidate_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(candidate_id="  "))

    def test_missing_reference_id_rejected(self):
        raw = dossier()
        del raw["reference_id"]
        with self.assertRaises(ValueError):
            normalize_dossier(raw)

    def test_a_candidate_cannot_reference_itself(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(reference_id="hyb-cand-01"))

    def test_non_boolean_approval_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(reference_approved="yes"))

    def test_negative_approval_age_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(reference_approval_age_months=-1.0))

    def test_non_finite_approval_age_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(reference_approval_age_months=float("inf")))

    def test_unknown_divergence_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(attributes=attributes(**{"sealing-method": "ish"})))

    def test_a_dossier_that_skips_a_decisive_attribute_is_rejected(self):
        partial = attributes()
        del partial["die-attach-process"]
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(attributes=partial))

    def test_attributes_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_dossier(dossier(attributes=["identical"]))


class DivergenceIndexTests(unittest.TestCase):
    def test_a_fully_identical_pair_indexes_at_zero(self):
        self.assertAlmostEqual(divergence_index(attributes()), 0.0, places=9)

    def test_a_fully_incompatible_pair_indexes_at_one(self):
        every = {a: "incompatible" for a in ATTRIBUTE_CRITICALITY}
        self.assertAlmostEqual(divergence_index(every), 1.0, places=9)

    def test_a_decisive_move_indexes_above_a_supporting_move(self):
        decisive = divergence_index(attributes(**{"package-family": "major-variant"}))
        supporting = dict(attributes())
        supporting["design-rule-set"] = "major-variant"
        self.assertGreater(decisive, divergence_index(supporting))

    def test_empty_attribute_set_rejected(self):
        with self.assertRaises(ValueError):
            divergence_index({})

    def test_the_index_never_leaves_the_unit_interval(self):
        index = divergence_index(attributes(**{"wire-bond-process": "major-variant"}))
        self.assertGreaterEqual(index + INDEX_TOLERANCE, 0.0)
        self.assertLessEqual(index - INDEX_TOLERANCE, 1.0)


class DeltaProgrammeTests(unittest.TestCase):
    def test_an_identical_pair_owes_no_delta_tests(self):
        self.assertEqual(delta_test_groups(attributes()), ())

    def test_a_moved_wire_bond_process_pulls_in_bond_pull(self):
        groups = delta_test_groups(attributes(**{"wire-bond-process": "minor-variant"}))
        self.assertIn("bond-pull-strength", groups)

    def test_a_moved_sealing_method_pulls_in_hermeticity(self):
        groups = delta_test_groups(attributes(**{"sealing-method": "major-variant"}))
        self.assertIn("hermeticity-and-seal", groups)

    def test_delta_groups_are_deduplicated_and_ordered(self):
        groups = delta_test_groups(
            attributes(
                **{"die-attach-process": "major-variant", "substrate-technology": "minor-variant"}
            )
        )
        self.assertEqual(list(groups), sorted(set(groups)))

    def test_no_delta_groups_means_no_delta_sample(self):
        self.assertEqual(delta_sample_size(attributes()), 0)

    def test_a_minor_variant_takes_the_base_sample(self):
        self.assertEqual(
            delta_sample_size(attributes(**{"design-rule-set": "minor-variant"})),
            BASE_DELTA_SAMPLE,
        )

    def test_every_major_variant_adds_to_the_sample(self):
        size = delta_sample_size(
            attributes(**{"package-family": "major-variant", "sealing-method": "major-variant"})
        )
        self.assertEqual(size, BASE_DELTA_SAMPLE + 2 * SAMPLE_PER_MAJOR_VARIANT)


class BlockingFindingTests(unittest.TestCase):
    def test_a_clean_dossier_has_no_blocking_finding(self):
        self.assertEqual(blocking_findings(dossier()), [])

    def test_an_unapproved_reference_blocks_the_route(self):
        self.assertIn(
            "reference-circuit-not-approved",
            blocking_findings(dossier(reference_approved=False)),
        )

    def test_an_aged_reference_approval_blocks_the_route(self):
        aged = dossier(reference_approval_age_months=REFERENCE_VALIDITY_MONTHS + 1.0)
        self.assertIn(
            "reference-approval-outside-validity-window", blocking_findings(aged)
        )

    def test_an_approval_exactly_on_the_validity_window_still_counts(self):
        edge = dossier(reference_approval_age_months=float(REFERENCE_VALIDITY_MONTHS))
        self.assertEqual(blocking_findings(edge), [])

    def test_a_less_demanding_reference_level_blocks_the_route(self):
        mismatch = dossier(
            candidate_quality_level="level-1", reference_quality_level="level-3"
        )
        self.assertIn(
            "reference-quality-level-below-candidate", blocking_findings(mismatch)
        )

    def test_a_more_demanding_reference_level_is_accepted(self):
        generous = dossier(
            candidate_quality_level="level-3", reference_quality_level="level-1"
        )
        self.assertEqual(blocking_findings(generous), [])

    def test_an_incompatible_decisive_attribute_blocks_the_route(self):
        blocked = dossier(attributes=attributes(**{"substrate-technology": "incompatible"}))
        self.assertIn("decisive-attribute-incompatible", blocking_findings(blocked))

    def test_too_many_decisive_major_variants_block_the_route(self):
        moved = {a: "major-variant" for a in decisive_attributes()}
        self.assertIn(
            "too-many-decisive-major-variants",
            blocking_findings(dossier(attributes=moved)),
        )

    def test_the_permitted_number_of_major_variants_does_not_block(self):
        names = decisive_attributes()[:MAX_MAJOR_VARIANT_ATTRIBUTES]
        moved = attributes(**{a: "major-variant" for a in names})
        self.assertEqual(blocking_findings(dossier(attributes=moved)), [])


class GoverningAttributeTests(unittest.TestCase):
    def test_the_worst_weighted_attribute_governs(self):
        moved = attributes(**{"die-attach-process": "major-variant"})
        moved["design-rule-set"] = "minor-variant"
        self.assertEqual(governing_attribute(moved), "die-attach-process")

    def test_empty_attribute_set_rejected(self):
        with self.assertRaises(ValueError):
            governing_attribute({})


class AssessSimilarityTests(unittest.TestCase):
    def test_an_identical_pair_takes_full_credit(self):
        result = assess_similarity(dossier())
        self.assertEqual(result["route"], ROUTE_FULL_CREDIT)
        self.assertEqual(result["delta_test_groups"], ())
        self.assertTrue(result["route_granted"])

    def test_a_moved_attribute_takes_the_partial_programme(self):
        result = assess_similarity(
            dossier(attributes=attributes(**{"package-family": "minor-variant"}))
        )
        self.assertEqual(result["route"], ROUTE_PARTIAL)
        self.assertIn("hermeticity-and-seal", result["delta_test_groups"])
        self.assertEqual(result["delta_sample_size"], BASE_DELTA_SAMPLE)

    def test_a_blocked_dossier_falls_back_to_the_full_programme(self):
        result = assess_similarity(dossier(reference_approved=False))
        self.assertEqual(result["route"], ROUTE_FULL)
        self.assertFalse(result["route_granted"])
        self.assertEqual(result["delta_test_groups"], ())

    def test_a_blocked_dossier_is_not_given_a_delta_sample(self):
        result = assess_similarity(dossier(reference_approved=False))
        self.assertEqual(result["delta_sample_size"], 0)

    def test_the_governing_attribute_is_reported(self):
        result = assess_similarity(
            dossier(attributes=attributes(**{"sealing-method": "major-variant"}))
        )
        self.assertEqual(result["governing_attribute"], "sealing-method")


class RankCandidatesTests(unittest.TestCase):
    def candidates(self):
        return [
            dossier(candidate_id="hyb-cand-01"),
            dossier(
                candidate_id="hyb-cand-02",
                attributes=attributes(**{"package-family": "major-variant"}),
            ),
            dossier(candidate_id="hyb-cand-03", reference_approved=False),
        ]

    def test_every_dossier_produces_a_record(self):
        report = rank_candidates(self.candidates())
        self.assertEqual(len(report["records"]), 3)

    def test_the_most_alike_candidate_ranks_first(self):
        report = rank_candidates(self.candidates())
        self.assertEqual(report["granted_order"][0], "hyb-cand-01")

    def test_a_refused_candidate_is_reported_with_its_reasons(self):
        report = rank_candidates(self.candidates())
        self.assertEqual(report["refused"][0]["candidate_id"], "hyb-cand-03")
        self.assertIn(
            "reference-circuit-not-approved", report["refused"][0]["findings"]
        )

    def test_the_campaign_groups_are_the_union_of_the_granted_deltas(self):
        report = rank_candidates(self.candidates())
        self.assertIn("hermeticity-and-seal", report["campaign_delta_groups"])

    def test_a_set_with_a_refusal_is_not_all_granted(self):
        self.assertFalse(rank_candidates(self.candidates())["all_granted"])

    def test_a_clean_set_is_all_granted(self):
        report = rank_candidates([dossier(candidate_id="hyb-cand-09")])
        self.assertTrue(report["all_granted"])

    def test_duplicate_candidate_id_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([dossier(), dossier()])

    def test_empty_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([])

    def test_non_sequence_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates(dossier())


if __name__ == "__main__":
    unittest.main()
