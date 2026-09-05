"""Contract test for the event-tree-analysis leaf (wave-41).

Exercises the SKILL.md workflow of the systems-engineering-safety/
arp4761a/event-tree-analysis leaf offline and deterministically:
step 1 fixes the initiating event frequency, step 2 lists the ordered
mitigating functions with their branch probabilities, step 3 enumerates
the full binary branch tree with build_paths, step 4 rolls up and ranks
the end-state frequencies with outcome_frequencies, step 5 sums the
failure end-state frequency with is_failure_end_state and
top_function_failure_frequency, and step 6 screens the ranked event-tree
sequences against the per-flight-hour severity target of each end
state's FHA class with dominant_sequences. All expected values are the
real module outputs from the smoke run against the cargo-fire worked
example (initiator frequency 3e-5 per flight hour) and the validation
list of the wave-41 spec.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import event_tree_analysis_logic as eta

FIRE_NODES = [("detect", 0.95), ("extinguish", 0.90), ("pilot", 0.80)]
INITIATOR = 3e-5
PROBABILITY_TABLE = {
    "detect:F extinguish:F pilot:F": 0.001,
    "detect:S extinguish:F pilot:F": 0.019,
    "detect:F extinguish:S pilot:F": 0.009,
    "detect:S extinguish:S pilot:F": 0.171,
    "detect:F extinguish:F pilot:S": 0.004,
    "detect:S extinguish:F pilot:S": 0.076,
    "detect:F extinguish:S pilot:S": 0.036,
    "detect:S extinguish:S pilot:S": 0.684,
}
FREQUENCY_TABLE = {
    "detect:S extinguish:S pilot:S": 2.052e-5,
    "detect:S extinguish:S pilot:F": 5.13e-6,
    "detect:S extinguish:F pilot:S": 2.28e-6,
    "detect:F extinguish:S pilot:S": 1.08e-6,
    "detect:S extinguish:F pilot:F": 5.7e-7,
    "detect:F extinguish:S pilot:F": 2.7e-7,
    "detect:F extinguish:F pilot:S": 1.2e-7,
    "detect:F extinguish:F pilot:F": 3e-8,
}
FAILURE_SEQUENCE = "detect:F extinguish:F pilot:F"


def fire_paths():
    """Full binary expansion over the three fire mitigating functions."""
    return eta.build_paths(FIRE_NODES)


def fire_frequencies():
    """Ranked end-state frequency rollup at the 3e-5 initiator."""
    return eta.outcome_frequencies(INITIATOR, FIRE_NODES)


class EventTreeAnalysisContractTest(unittest.TestCase):
    """Contract tests for the event-tree-analysis leaf logic."""

    # ---- step 3: binary branch tree enumeration with build_paths ----

    def test_build_paths_fire_path_count_and_keys(self):
        """Step 3 of the SKILL.md workflow, the binary branch-tree
        enumeration with build_paths over the cargo fire nodes, yields
        the full 2**3 = 8 end-state paths with exactly the keys
        sequence, path and probability per entry."""
        paths = fire_paths()
        self.assertEqual(len(paths), 8)
        for entry in paths:
            self.assertEqual(
                set(entry.keys()), {"sequence", "path", "probability"}
            )
        self.assertEqual(len({entry["sequence"] for entry in paths}), 8)

    def test_build_paths_fire_enumeration_order_is_binary_mask(self):
        """Step 3 of the SKILL.md workflow enumerates end-state paths as
        the ascending binary mask with node i mapped to bit i, so the
        all-failure path comes first and the all-success path last."""
        paths = fire_paths()
        self.assertEqual(paths[0]["sequence"], FAILURE_SEQUENCE)
        self.assertEqual(paths[0]["path"], (False, False, False))
        self.assertEqual(
            paths[-1]["sequence"], "detect:S extinguish:S pilot:S"
        )
        self.assertEqual(paths[-1]["path"], (True, True, True))
        self.assertEqual(
            [entry["path"] for entry in paths][1], (True, False, False)
        )
        self.assertEqual(
            [entry["path"] for entry in paths][4], (False, False, True)
        )

    def test_build_paths_fire_probabilities_match_table(self):
        """Step 3 of the SKILL.md workflow multiplies the branch
        probabilities (p for a success branch, 1 - p for a failure
        branch) along each enumerated path; every path probability of
        the cargo fire tree matches the tabulated value within 1e-12."""
        for entry in fire_paths():
            self.assertAlmostEqual(
                entry["probability"],
                PROBABILITY_TABLE[entry["sequence"]],
                delta=1e-12,
            )

    def test_build_paths_probability_sum_is_exactly_one(self):
        """Step 3 of the SKILL.md workflow partitions the initiator: the
        path probabilities of the full binary expansion sum to exactly
        1.0 (real module output of the smoke run)."""
        total = sum(entry["probability"] for entry in fire_paths())
        self.assertEqual(total, 1.0)

    def test_build_paths_single_node_two_paths(self):
        """Step 3 of the SKILL.md workflow expands a single mitigating
        function into the success and failure end-state paths with
        probabilities p and 1 - p."""
        paths = eta.build_paths([("g", 0.7)])
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0]["sequence"], "g:F")
        self.assertAlmostEqual(paths[0]["probability"], 0.3, delta=1e-15)
        self.assertEqual(paths[1]["sequence"], "g:S")
        self.assertAlmostEqual(paths[1]["probability"], 0.7, delta=1e-15)

    def test_all_failure_path_probability_is_failure_product(self):
        """Step 3 of the SKILL.md workflow: the all-failure end-state
        path probability equals the product of the failure probabilities
        1 - p over the nodes (0.05 x 0.10 x 0.20) within 1e-15, the
        identity behind the failure end-state frequency sum."""
        paths = fire_paths()
        fff = next(
            entry for entry in paths if entry["sequence"] == FAILURE_SEQUENCE
        )
        self.assertAlmostEqual(
            fff["probability"], 0.05 * 0.10 * 0.20, delta=1e-15
        )

    # ---- step 4: end-state frequency rollup with outcome_frequencies ----

    def test_outcome_frequencies_entry_count_and_keys(self):
        """Step 4 of the SKILL.md workflow rolls up one frequency per
        enumerated end-state path with exactly the keys sequence, path,
        probability and frequency per entry."""
        entries = fire_frequencies()
        self.assertEqual(len(entries), 8)
        for entry in entries:
            self.assertEqual(
                set(entry.keys()), {"sequence", "path", "probability",
                                    "frequency"}
            )

    def test_outcome_frequencies_fire_table(self):
        """Step 4 of the SKILL.md workflow computes frequency =
        initiator frequency x path probability; all eight end-state
        frequencies of the cargo fire rollup match the tabulated values
        within 1e-12 and sum to the initiator frequency 3e-5."""
        entries = fire_frequencies()
        self.assertAlmostEqual(
            sum(entry["frequency"] for entry in entries),
            INITIATOR,
            delta=1e-15,
        )
        for entry in entries:
            self.assertAlmostEqual(
                entry["frequency"],
                FREQUENCY_TABLE[entry["sequence"]],
                delta=1e-12,
            )

    def test_outcome_frequencies_ranked_descending(self):
        """Step 4 of the SKILL.md workflow ranks the end-state paths by
        descending frequency, so the ranked list is non-increasing."""
        entries = fire_frequencies()
        frequencies = [entry["frequency"] for entry in entries]
        self.assertEqual(
            frequencies,
            sorted(frequencies, reverse=True),
        )

    def test_outcome_frequencies_sum_equals_initiator_exactly(self):
        """Step 4 of the SKILL.md workflow partitions the initiating
        event: the end-state frequencies sum to the initiator
        frequency 3e-05 within 1e-15 (order-insensitive float check)."""
        total = sum(entry["frequency"] for entry in fire_frequencies())
        self.assertAlmostEqual(total, 3e-05, delta=1e-15)

    def test_outcome_frequencies_single_node_even_split_tie(self):
        """Step 4 of the SKILL.md workflow: a single node with success
        probability 0.5 at initiator 1e-5 splits the initiating event
        evenly into two end states, g:F at 5e-6 then g:S at 5e-6, with
        the tie keeping enumeration order (stable rank)."""
        entries = eta.outcome_frequencies(1e-5, [("g", 0.5)])
        self.assertEqual(
            [entry["sequence"] for entry in entries], ["g:F", "g:S"]
        )
        self.assertEqual(entries[0]["frequency"], 5e-6)
        self.assertEqual(entries[1]["frequency"], 5e-6)

    def test_outcome_frequencies_two_node_ties_keep_enumeration_order(self):
        """Step 4 of the SKILL.md workflow breaks equal end-state
        frequencies by enumeration order: with two p = 0.5 nodes all
        four frequencies tie and the ranked list keeps the ascending
        mask order a:F b:F, a:S b:F, a:F b:S, a:S b:S."""
        entries = eta.outcome_frequencies(1.0, [("a", 0.5), ("b", 0.5)])
        self.assertEqual(
            [entry["sequence"] for entry in entries],
            ["a:F b:F", "a:S b:F", "a:F b:S", "a:S b:S"],
        )
        for entry in entries:
            self.assertEqual(entry["frequency"], 0.25)

    def test_boundary_success_probability_one(self):
        """Step 2 of the SKILL.md workflow admits the boundary branch
        probability p = 1.0: the function always succeeds, so the
        success end state carries the whole initiator frequency."""
        entries = eta.outcome_frequencies(INITIATOR, [("a", 1.0)])
        self.assertEqual(entries[0]["sequence"], "a:S")
        self.assertEqual(entries[0]["frequency"], INITIATOR)
        self.assertEqual(entries[1]["sequence"], "a:F")
        self.assertEqual(entries[1]["frequency"], 0.0)

    def test_boundary_success_probability_zero(self):
        """Step 2 of the SKILL.md workflow admits the boundary branch
        probability p = 0.0: the function always fails, so the failure
        end state carries the whole initiator frequency."""
        entries = eta.outcome_frequencies(INITIATOR, [("a", 0.0)])
        self.assertEqual(entries[0]["sequence"], "a:F")
        self.assertEqual(entries[0]["frequency"], INITIATOR)
        self.assertEqual(entries[1]["sequence"], "a:S")
        self.assertEqual(entries[1]["frequency"], 0.0)

    def test_zero_initiator_frequency_is_legal(self):
        """Step 1 of the SKILL.md workflow rejects negative but admits a
        zero initiator frequency: every end-state frequency rolls up to
        0.0 without error."""
        entries = eta.outcome_frequencies(0.0, FIRE_NODES)
        self.assertEqual(len(entries), 8)
        for entry in entries:
            self.assertEqual(entry["frequency"], 0.0)

    # ---- step 5: failure end-state frequency sum ----

    def test_is_failure_end_state_all_false(self):
        """Step 5 of the SKILL.md workflow: is_failure_end_state returns
        True exactly when every outcome on the path is False, the end
        state where no mitigating function contained the initiator."""
        self.assertTrue(eta.is_failure_end_state((False, False, False)))
        self.assertTrue(eta.is_failure_end_state((False,)))

    def test_is_failure_end_state_any_success_false(self):
        """Step 5 of the SKILL.md workflow: any success outcome on the
        path means the initiator was contained somewhere along the
        chain, so the path is not the failure end state."""
        self.assertFalse(eta.is_failure_end_state((True, False, False)))
        self.assertFalse(eta.is_failure_end_state((False, True, False)))
        self.assertFalse(eta.is_failure_end_state((False, False, True)))
        self.assertFalse(eta.is_failure_end_state((True, True, True)))

    def test_top_function_failure_frequency_fire_sum(self):
        """Step 5 of the SKILL.md workflow sums the frequency over the
        paths that reach the failure end state: the cargo fire rollup
        returns sequences [detect:F extinguish:F pilot:F] with frequency
        3e-8 per flight hour within 1e-15."""
        result = eta.top_function_failure_frequency(fire_frequencies())
        self.assertEqual(result["sequences"], [FAILURE_SEQUENCE])
        self.assertAlmostEqual(result["frequency"], 3e-8, delta=1e-15)

    def test_top_function_failure_frequency_initiator_product_identity(self):
        """Step 5 of the SKILL.md workflow: the failure end-state
        frequency equals the initiator frequency times the product of
        the failure probabilities, 3e-5 x 0.05 x 0.10 x 0.20, within
        1e-15 (the spec identity for the rollup)."""
        result = eta.top_function_failure_frequency(fire_frequencies())
        expected = INITIATOR * 0.05 * 0.10 * 0.20
        self.assertAlmostEqual(result["frequency"], expected, delta=1e-15)

    # ---- step 6: dominant-sequence screening with dominant_sequences ----

    def test_dominant_sequences_flags_failure_end_vs_catastrophic(self):
        """Step 6 of the SKILL.md workflow screens each ranked event-tree
        sequence against the severity target of its FHA class: the
        failure end-state frequency 3e-8 strictly exceeds the
        catastrophic target 1e-9 and is flagged dominant with ratio
        30.0 within 1e-9 (mitigation required)."""
        dominant = eta.dominant_sequences(
            fire_frequencies(), eta.CATASTROPHIC
        )
        flagged = {entry["sequence"]: entry for entry in dominant}
        self.assertIn(FAILURE_SEQUENCE, flagged)
        self.assertAlmostEqual(
            flagged[FAILURE_SEQUENCE]["ratio"], 30.0, delta=1e-9
        )

    def test_dominant_sequences_flags_hazardous_fail_path(self):
        """Step 6 of the SKILL.md workflow: the undetected but
        extinguished-late end state detect:F extinguish:F pilot:S sits
        at 1.2e-7, strictly above the hazardous target 1e-7, and is
        flagged dominant with ratio 1.2 within 1e-9 (thin margin)."""
        dominant = eta.dominant_sequences(fire_frequencies(), eta.HAZARDOUS)
        flagged = {entry["sequence"]: entry for entry in dominant}
        self.assertIn("detect:F extinguish:F pilot:S", flagged)
        self.assertAlmostEqual(
            flagged["detect:F extinguish:F pilot:S"]["ratio"],
            1.2,
            delta=1e-9,
        )

    def test_dominant_sequences_all_success_not_dominant_vs_minor(self):
        """Step 6 of the SKILL.md workflow screens the extinguish-success
        end states against the minor target 1e-3: the largest of them,
        the all-success chain at 2.052e-5, stays below the target, so
        nothing is flagged dominant against MINOR."""
        dominant = eta.dominant_sequences(fire_frequencies(), eta.MINOR)
        self.assertEqual(dominant, [])

    def test_dominant_sequences_whole_list_screening_caution(self):
        """Step 6 of the SKILL.md workflow demonstrates the global
        screening caution: screening the whole ranked list against the
        major target 1e-5 flags only the all-success end state (2.052e-5
        exceeds 1e-5), which is not the dangerous sequence, so each end
        state must be screened against its own FHA class target."""
        dominant = eta.dominant_sequences(fire_frequencies(), eta.MAJOR)
        self.assertEqual(
            [entry["sequence"] for entry in dominant],
            ["detect:S extinguish:S pilot:S"],
        )

    def test_dominant_sequences_equality_with_target_not_dominant(self):
        """Step 6 of the SKILL.md workflow uses a strict comparison: an
        end-state frequency sitting exactly on its severity target is
        NOT dominant (equality is not dominant)."""
        fixture = [
            {
                "sequence": "x:F",
                "path": (False,),
                "probability": 1.0,
                "frequency": eta.MAJOR,
            }
        ]
        dominant = eta.dominant_sequences(fixture, eta.MAJOR)
        self.assertEqual(dominant, [])

    def test_dominant_sequences_result_order_matches_input(self):
        """Step 6 of the SKILL.md workflow returns the dominant
        sequences in the input frequency-descending order, so the
        highest-frequency dominant sequence is reported first."""
        fixture = [
            {"sequence": "a:F", "path": (False,), "probability": 1.0,
             "frequency": 2e-5},
            {"sequence": "b:F", "path": (False,), "probability": 1.0,
             "frequency": 1.5e-5},
            {"sequence": "c:S", "path": (True,), "probability": 1.0,
             "frequency": 5e-6},
        ]
        dominant = eta.dominant_sequences(fixture, eta.MAJOR)
        self.assertEqual(
            [entry["sequence"] for entry in dominant], ["a:F", "b:F"]
        )
        self.assertAlmostEqual(
            dominant[0]["ratio"], 2e-5 / eta.MAJOR, delta=1e-9
        )

    # ---- value error rejection of non-physical inputs ----

    def test_valueerror_negative_initiator_frequency(self):
        """Step 1 of the SKILL.md workflow rejects a negative initiating
        event frequency as non-physical with ValueError."""
        with self.assertRaises(ValueError):
            eta.outcome_frequencies(-1.0, FIRE_NODES)

    def test_valueerror_empty_node_list(self):
        """Steps 3 and 4 of the SKILL.md workflow reject an empty
        mitigating-function list: both build_paths and
        outcome_frequencies raise ValueError."""
        with self.assertRaises(ValueError):
            eta.build_paths([])
        with self.assertRaises(ValueError):
            eta.outcome_frequencies(INITIATOR, [])

    def test_valueerror_node_count_above_branch_max(self):
        """Steps 3 and 4 of the SKILL.md workflow cap the expansion at
        BRANCH_NODES_MAX = 12 nodes: 13 branch nodes (8192 paths) raise
        ValueError in both build_paths and outcome_frequencies."""
        thirteen = [("n%d" % index, 0.5) for index in range(13)]
        with self.assertRaises(ValueError):
            eta.build_paths(thirteen)
        with self.assertRaises(ValueError):
            eta.outcome_frequencies(INITIATOR, thirteen)

    def test_valueerror_branch_probability_out_of_range(self):
        """Step 2 of the SKILL.md workflow rejects a branch success
        probability outside [0, 1]: both p = 1.5 and p = -0.1 raise
        ValueError in build_paths and outcome_frequencies."""
        for bad_probability in (1.5, -0.1):
            with self.assertRaises(ValueError):
                eta.build_paths([("x", bad_probability)])
            with self.assertRaises(ValueError):
                eta.outcome_frequencies(INITIATOR, [("x", bad_probability)])

    def test_valueerror_severity_target_not_positive(self):
        """Step 6 of the SKILL.md workflow rejects a non-positive
        severity target: both zero and negative targets raise
        ValueError in dominant_sequences."""
        with self.assertRaises(ValueError):
            eta.dominant_sequences(fire_frequencies(), 0.0)
        with self.assertRaises(ValueError):
            eta.dominant_sequences(fire_frequencies(), -1e-9)

    # ---- boundary expansion and determinism ----

    def test_twelve_node_expansion_cap_boundary(self):
        """Step 3 of the SKILL.md workflow expands the largest legal
        tree: 12 branch nodes at p = 0.5 give 4096 end-state paths, the
        all-success probability is exactly 2**-12 = 0.000244140625, and
        the ranked rollup maximum frequency is 2**-12."""
        twelve = [("n%d" % index, 0.5) for index in range(12)]
        paths = eta.build_paths(twelve)
        self.assertEqual(len(paths), 4096)
        self.assertEqual(paths[-1]["path"], (True,) * 12)
        self.assertEqual(paths[-1]["probability"], 2.0 ** -12)
        entries = eta.outcome_frequencies(1.0, twelve)
        self.assertEqual(entries[0]["frequency"], 2.0 ** -12)
        total = sum(entry["frequency"] for entry in entries)
        self.assertAlmostEqual(total, 1.0, delta=1e-15)

    def test_determinism_repeated_calls_equal(self):
        """Steps 3 and 4 of the SKILL.md workflow are deterministic:
        repeated calls return equal structures, so the event-tree rollup
        is reproducible offline."""
        self.assertEqual(fire_paths(), fire_paths())
        self.assertEqual(fire_frequencies(), fire_frequencies())

    def test_fixed_sequence_strings_stable(self):
        """Step 3 of the SKILL.md workflow renders every end-state path
        as a fixed readable sequence string in node order with S and F
        markers, stable across the enumeration."""
        sequences = [entry["sequence"] for entry in fire_paths()]
        self.assertEqual(
            sequences,
            [
                "detect:F extinguish:F pilot:F",
                "detect:S extinguish:F pilot:F",
                "detect:F extinguish:S pilot:F",
                "detect:S extinguish:S pilot:F",
                "detect:F extinguish:F pilot:S",
                "detect:S extinguish:F pilot:S",
                "detect:F extinguish:S pilot:S",
                "detect:S extinguish:S pilot:S",
            ],
        )


if __name__ == "__main__":
    unittest.main()
