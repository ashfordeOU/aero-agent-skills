"""Contract tests for the clause 4 off-the-shelf item selection process logic."""

import unittest

from q2010_process_logic import (
    CONDITIONAL_ARTEFACT,
    KNOWN_ARTEFACTS,
    MAKE_OR_BUY,
    QUALIFICATION_STATES,
    STAGE_ORDER,
    STAGES,
    assess_ots_process,
    normalise_identifier,
    product_tree_findings,
    required_artefacts,
    sequence_findings,
    stage_completion,
    stage_index,
    stage_reached,
    validate_candidates,
    validate_product_tree,
)

TREE = [
    {"node": "pcdu", "make_or_buy": "buy-ots"},
    {"node": "structure-panel", "make_or_buy": "make"},
    {"node": "star-tracker", "make_or_buy": "buy-custom"},
]


def evidence_through(stage, status="qualified-for-this-application"):
    held = []
    for name in STAGE_ORDER:
        held.extend(required_artefacts(name, status))
        if name == stage:
            break
    return held


def candidate(ref="cand-1", node="pcdu", status="qualified-for-this-application",
              stage="procurement-and-qualification", evidence=None):
    return {
        "candidate": ref,
        "node": node,
        "qualification_status": status,
        "evidence": evidence if evidence is not None else evidence_through(stage, status),
    }


class NormaliseTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier("  PCDU ", "x"), "pcdu")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(1, "x")


class StageModelTests(unittest.TestCase):
    def test_stage_order_matches_the_stage_table(self):
        self.assertEqual(STAGE_ORDER, tuple(name for name, _a in STAGES))

    def test_indices_are_sequential(self):
        self.assertEqual([stage_index(s) for s in STAGE_ORDER], list(range(len(STAGE_ORDER))))

    def test_market_investigation_precedes_selection(self):
        self.assertLess(
            stage_index("market-investigation"),
            stage_index("characterization-and-selection"),
        )

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_index("negotiation")

    def test_every_stage_artefact_is_a_known_artefact(self):
        for _name, artefacts in STAGES:
            for artefact in artefacts:
                self.assertIn(artefact, KNOWN_ARTEFACTS)


class ConditionalArtefactTests(unittest.TestCase):
    def test_item_qualified_for_this_application_owes_no_delta_plan(self):
        owed = required_artefacts(
            "procurement-and-qualification", "qualified-for-this-application"
        )
        self.assertNotIn(CONDITIONAL_ARTEFACT, owed)

    def test_item_qualified_elsewhere_owes_a_delta_plan(self):
        owed = required_artefacts(
            "procurement-and-qualification", "qualified-for-another-application"
        )
        self.assertIn(CONDITIONAL_ARTEFACT, owed)

    def test_unqualified_item_owes_a_delta_plan(self):
        owed = required_artefacts("procurement-and-qualification", "not-qualified")
        self.assertIn(CONDITIONAL_ARTEFACT, owed)

    def test_earlier_stages_are_unaffected_by_the_state(self):
        self.assertEqual(
            required_artefacts("market-investigation", "not-qualified"),
            required_artefacts("market-investigation"),
        )

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            required_artefacts("procurement-and-qualification", "probably-fine")


class ProductTreeValidationTests(unittest.TestCase):
    def test_nodes_are_keyed_by_identifier(self):
        nodes = validate_product_tree(TREE)
        self.assertEqual(nodes["pcdu"]["make_or_buy"], "buy-ots")

    def test_duplicate_node_rejected(self):
        with self.assertRaises(ValueError):
            validate_product_tree(TREE + [{"node": "PCDU", "make_or_buy": "make"}])

    def test_unknown_make_or_buy_rejected(self):
        with self.assertRaises(ValueError):
            validate_product_tree([{"node": "pcdu", "make_or_buy": "borrow"}])

    def test_empty_tree_rejected(self):
        with self.assertRaises(ValueError):
            validate_product_tree([])

    def test_every_declared_decision_is_accepted(self):
        for decision in MAKE_OR_BUY:
            nodes = validate_product_tree([{"node": "n", "make_or_buy": decision}])
            self.assertEqual(nodes["n"]["make_or_buy"], decision)


class CandidateValidationTests(unittest.TestCase):
    def test_evidence_becomes_a_set(self):
        cands = validate_candidates([candidate(evidence=["candidate-list", "candidate-list"])])
        self.assertEqual(cands["cand-1"]["evidence"], frozenset({"candidate-list"}))

    def test_duplicate_candidate_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidates([candidate(), candidate(ref="CAND-1")])

    def test_unknown_artefact_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidates([candidate(evidence=["vendor-brochure"])])

    def test_unknown_qualification_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidates([candidate(status="looks-fine")])

    def test_non_collection_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidates([candidate(evidence="candidate-list")])

    def test_every_declared_state_is_accepted(self):
        for state in QUALIFICATION_STATES:
            cands = validate_candidates([candidate(status=state)])
            self.assertEqual(cands["cand-1"]["qualification_status"], state)


class StageProgressTests(unittest.TestCase):
    def test_full_evidence_reaches_the_last_stage(self):
        cands = validate_candidates([candidate()])
        completion = stage_completion(cands["cand-1"])
        self.assertEqual(stage_reached(completion), "procurement-and-qualification")

    def test_partial_evidence_stops_at_the_first_stage(self):
        cands = validate_candidates([candidate(stage="market-investigation")])
        completion = stage_completion(cands["cand-1"])
        self.assertEqual(stage_reached(completion), "market-investigation")

    def test_no_evidence_reaches_no_stage(self):
        cands = validate_candidates([candidate(evidence=[])])
        self.assertIsNone(stage_reached(stage_completion(cands["cand-1"])))

    def test_missing_delta_plan_holds_the_last_stage_open(self):
        held = [a for a in evidence_through("procurement-and-qualification", "not-qualified")
                if a != CONDITIONAL_ARTEFACT]
        cands = validate_candidates([candidate(status="not-qualified", evidence=held)])
        completion = stage_completion(cands["cand-1"])
        self.assertEqual(stage_reached(completion), "characterization-and-selection")
        self.assertEqual(completion[2]["missing"], (CONDITIONAL_ARTEFACT,))

    def test_later_evidence_does_not_promote_past_an_open_stage(self):
        held = list(required_artefacts("market-investigation"))
        held.extend(required_artefacts("procurement-and-qualification"))
        cands = validate_candidates([candidate(evidence=held)])
        self.assertEqual(stage_reached(stage_completion(cands["cand-1"])), "market-investigation")

    def test_malformed_candidate_rejected(self):
        with self.assertRaises(ValueError):
            stage_completion("cand-1")


class SequenceFindingTests(unittest.TestCase):
    def test_out_of_sequence_evidence_is_advisory(self):
        held = list(required_artefacts("market-investigation"))
        held.extend(required_artefacts("procurement-and-qualification"))
        cands = validate_candidates([candidate(evidence=held)])
        findings = sequence_findings("cand-1", stage_completion(cands["cand-1"]))
        self.assertEqual(findings[0]["code"], "stage-evidence-out-of-sequence")
        self.assertEqual(findings[0]["severity"], "advisory")

    def test_orderly_progress_has_no_sequence_finding(self):
        cands = validate_candidates([candidate(stage="characterization-and-selection")])
        self.assertEqual(sequence_findings("cand-1", stage_completion(cands["cand-1"])), [])

    def test_malformed_completion_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings("cand-1", "complete")


class ProductTreeReconciliationTests(unittest.TestCase):
    def test_candidate_on_a_buy_ots_node_is_clean(self):
        nodes = validate_product_tree([{"node": "pcdu", "make_or_buy": "buy-ots"}])
        cands = validate_candidates([candidate()])
        self.assertEqual(product_tree_findings(nodes, cands), [])

    def test_candidate_on_a_make_node_blocks(self):
        nodes = validate_product_tree(TREE)
        cands = validate_candidates([candidate(ref="c1", node="pcdu"),
                                     candidate(ref="c2", node="structure-panel")])
        codes = [f["code"] for f in product_tree_findings(nodes, cands)]
        self.assertIn("ots-candidate-on-make-node", codes)

    def test_candidate_on_a_custom_buy_node_is_advisory(self):
        nodes = validate_product_tree(TREE)
        cands = validate_candidates([candidate(ref="c1", node="pcdu"),
                                     candidate(ref="c2", node="star-tracker")])
        findings = [f for f in product_tree_findings(nodes, cands)
                    if f["code"] == "ots-candidate-on-custom-buy-node"]
        self.assertEqual(findings[0]["severity"], "advisory")

    def test_candidate_on_an_unknown_node_blocks(self):
        nodes = validate_product_tree(TREE)
        cands = validate_candidates([candidate(ref="c1", node="pcdu"),
                                     candidate(ref="c2", node="reaction-wheel")])
        codes = [f["code"] for f in product_tree_findings(nodes, cands)]
        self.assertIn("candidate-node-not-in-product-tree", codes)

    def test_buy_ots_node_with_no_candidate_blocks(self):
        nodes = validate_product_tree(TREE)
        codes = [f["code"] for f in product_tree_findings(nodes, {})]
        self.assertIn("buy-ots-node-without-candidate", codes)

    def test_empty_tree_rejected(self):
        with self.assertRaises(ValueError):
            product_tree_findings({}, {})


class AssessmentTests(unittest.TestCase):
    def test_complete_process_on_a_matching_tree(self):
        result = assess_ots_process({
            "product_tree": [{"node": "pcdu", "make_or_buy": "buy-ots"}],
            "candidates": [candidate()],
        })
        self.assertEqual(result["decision"], "process-complete")
        self.assertAlmostEqual(result["process_maturity"], 1.0, places=9)

    def test_partial_process_is_incomplete(self):
        result = assess_ots_process({
            "product_tree": [{"node": "pcdu", "make_or_buy": "buy-ots"}],
            "candidates": [candidate(stage="market-investigation")],
        })
        self.assertEqual(result["decision"], "process-incomplete")
        self.assertAlmostEqual(result["process_maturity"], 1.0 / 3.0, places=9)
        self.assertEqual(result["incomplete_candidates"], ("cand-1",))

    def test_make_node_contradiction_is_not_integrated(self):
        result = assess_ots_process({
            "product_tree": TREE,
            "candidates": [candidate(ref="c1", node="pcdu"),
                           candidate(ref="c2", node="structure-panel")],
        })
        self.assertEqual(result["decision"], "process-not-integrated")

    def test_maturity_averages_over_the_candidates(self):
        result = assess_ots_process({
            "product_tree": [{"node": "pcdu", "make_or_buy": "buy-ots"},
                             {"node": "gps-rx", "make_or_buy": "buy-ots"}],
            "candidates": [candidate(ref="c1", node="pcdu"),
                           candidate(ref="c2", node="gps-rx",
                                     stage="characterization-and-selection")],
        })
        self.assertAlmostEqual(result["process_maturity"], 5.0 / 6.0, places=9)

    def test_no_candidates_leaves_the_process_incomplete(self):
        result = assess_ots_process({
            "product_tree": [{"node": "structure-panel", "make_or_buy": "make"}],
            "candidates": [],
        })
        self.assertEqual(result["decision"], "process-incomplete")
        self.assertAlmostEqual(result["process_maturity"], 0.0, places=9)

    def test_missing_product_tree_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_ots_process({"candidates": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_ots_process(["product_tree"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
