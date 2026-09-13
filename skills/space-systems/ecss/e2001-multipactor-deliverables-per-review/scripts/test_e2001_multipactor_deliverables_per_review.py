"""Gate 3 contract test for e2001-multipactor-deliverables-per-review.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_multipactor_deliverables_per_review.py
"""

import unittest

import e2001_multipactor_deliverables_per_review_logic as logic

TEST_ROUTE = ("multipactor-test",)
ANALYSIS_ROUTE = ("susceptibility-analysis",)
SIMILARITY_ROUTE = ("similarity-justification",)


class CatalogueTests(unittest.TestCase):
    def test_catalogue_holds_every_known_data_item(self):
        names = logic.catalogue()
        self.assertIn("multipactor-critical-item-list", names)
        self.assertIn("multipactor-verification-plan", names)
        self.assertIn("multipactor-free-declaration", names)
        self.assertIn("multipactor-test-procedure", names)
        self.assertIn("multipactor-test-report", names)
        self.assertIn("similarity-justification-dossier", names)
        self.assertEqual(len(names), 8)

    def test_catalogue_is_sorted(self):
        names = logic.catalogue()
        self.assertEqual(list(names), sorted(names))


class GateNormalisationTests(unittest.TestCase):
    def test_short_code_passes_through(self):
        self.assertEqual(logic.normalize_gate("cdr"), "cdr")

    def test_long_name_resolves_to_short_code(self):
        self.assertEqual(logic.normalize_gate("preliminary-design-review"), "pdr")

    def test_case_and_whitespace_are_absorbed(self):
        self.assertEqual(logic.normalize_gate("  QR "), "qr")

    def test_unknown_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_gate("frr")

    def test_non_string_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_gate(3)

    def test_empty_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_gate("   ")

    def test_gate_index_follows_the_review_sequence(self):
        self.assertLess(logic.gate_index("srr"), logic.gate_index("pdr"))
        self.assertLess(logic.gate_index("pdr"), logic.gate_index("cdr"))
        self.assertLess(logic.gate_index("cdr"), logic.gate_index("qr"))
        self.assertLess(logic.gate_index("qr"), logic.gate_index("ar"))


class RouteNormalisationTests(unittest.TestCase):
    def test_known_route_is_canonicalised(self):
        self.assertEqual(logic.normalize_route(" Multipactor-Test "), "multipactor-test")

    def test_unknown_route_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_route("inspection")

    def test_routes_are_sorted_and_deduplicated(self):
        got = logic.normalize_routes(
            ["similarity-justification", "multipactor-test", "multipactor-test"]
        )
        self.assertEqual(got, ("multipactor-test", "similarity-justification"))

    def test_single_route_string_is_accepted(self):
        self.assertEqual(logic.normalize_routes("multipactor-test"), TEST_ROUTE)

    def test_empty_route_declaration_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_routes([])

    def test_non_iterable_route_declaration_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_routes(7)


class MaturityTests(unittest.TestCase):
    def test_maturity_tokens_are_canonicalised(self):
        self.assertEqual(logic.normalize_maturity(" Approved "), "approved")

    def test_unknown_maturity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_maturity("preliminary")

    def test_maturity_rank_is_ordered(self):
        self.assertLess(logic.maturity_rank("draft"), logic.maturity_rank("issued"))
        self.assertLess(logic.maturity_rank("issued"), logic.maturity_rank("approved"))


class OwedSetTests(unittest.TestCase):
    def test_test_route_adds_procedure_and_report(self):
        owed = logic.owed_items(TEST_ROUTE)
        self.assertIn("multipactor-test-procedure", owed)
        self.assertIn("multipactor-test-report", owed)
        self.assertNotIn("similarity-justification-dossier", owed)

    def test_analysis_route_adds_yield_data_package(self):
        owed = logic.owed_items(ANALYSIS_ROUTE)
        self.assertIn("multipactor-susceptibility-analysis-report", owed)
        self.assertIn("secondary-emission-yield-data-package", owed)
        self.assertNotIn("multipactor-test-report", owed)

    def test_similarity_route_adds_the_dossier_only(self):
        owed = logic.owed_items(SIMILARITY_ROUTE)
        self.assertIn("similarity-justification-dossier", owed)
        self.assertNotIn("multipactor-test-procedure", owed)

    def test_route_independent_items_are_always_owed(self):
        for routes in (TEST_ROUTE, ANALYSIS_ROUTE, SIMILARITY_ROUTE):
            owed = logic.owed_items(routes)
            self.assertIn("multipactor-critical-item-list", owed)
            self.assertIn("multipactor-verification-plan", owed)
            self.assertIn("multipactor-free-declaration", owed)

    def test_combined_routes_union_their_items(self):
        owed = logic.owed_items(["multipactor-test", "similarity-justification"])
        self.assertIn("multipactor-test-report", owed)
        self.assertIn("similarity-justification-dossier", owed)


class WindowTests(unittest.TestCase):
    def test_unknown_data_item_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.deliverable_window("multipactor-brochure", TEST_ROUTE)

    def test_item_from_an_undeclared_route_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.deliverable_window("similarity-justification-dossier", TEST_ROUTE)

    def test_window_is_first_then_final_gate(self):
        first, final = logic.deliverable_window("multipactor-test-procedure", TEST_ROUTE)
        self.assertEqual(first, "cdr")
        self.assertEqual(final, "qr")


class RequiredMaturityTests(unittest.TestCase):
    def test_item_before_its_first_gate_is_not_due(self):
        self.assertIsNone(
            logic.required_maturity("multipactor-verification-plan", "srr", TEST_ROUTE)
        )

    def test_first_gate_requires_a_draft(self):
        self.assertEqual(
            logic.required_maturity("multipactor-verification-plan", "pdr", TEST_ROUTE),
            "draft",
        )

    def test_intermediate_gate_requires_an_issued_document(self):
        self.assertEqual(
            logic.required_maturity("multipactor-critical-item-list", "pdr", TEST_ROUTE),
            "issued",
        )

    def test_final_gate_requires_approval(self):
        self.assertEqual(
            logic.required_maturity("multipactor-critical-item-list", "cdr", TEST_ROUTE),
            "approved",
        )

    def test_after_the_final_gate_approval_still_stands(self):
        self.assertEqual(
            logic.required_maturity("multipactor-critical-item-list", "ar", TEST_ROUTE),
            "approved",
        )

    def test_single_gate_window_requires_approval_immediately(self):
        self.assertEqual(
            logic.required_maturity("multipactor-test-report", "qr", TEST_ROUTE),
            "approved",
        )


class ExpectedSetTests(unittest.TestCase):
    def test_only_the_item_list_is_due_at_the_first_gate(self):
        expected = logic.expected_deliverables("srr", TEST_ROUTE)
        self.assertEqual(expected, {"multipactor-critical-item-list": "draft"})

    def test_qualification_review_pulls_in_the_test_report(self):
        expected = logic.expected_deliverables("qr", TEST_ROUTE)
        self.assertEqual(expected["multipactor-test-report"], "approved")
        self.assertEqual(expected["multipactor-free-declaration"], "draft")

    def test_acceptance_review_owes_the_whole_declared_set(self):
        expected = logic.expected_deliverables("ar", TEST_ROUTE)
        self.assertEqual(len(expected), 5)
        self.assertTrue(all(v == "approved" for v in expected.values()))

    def test_schedule_covers_every_gate(self):
        schedule = logic.deliverable_schedule(ANALYSIS_ROUTE)
        self.assertEqual(tuple(schedule), logic.GATE_SEQUENCE)
        self.assertEqual(len(schedule["srr"]), 1)
        self.assertEqual(len(schedule["pdr"]), 4)


class SubmissionNormalisationTests(unittest.TestCase):
    def test_mapping_form_is_accepted(self):
        got = logic.normalize_submissions({"multipactor-test-report": "approved"})
        self.assertEqual(got, {"multipactor-test-report": "approved"})

    def test_row_form_is_accepted(self):
        got = logic.normalize_submissions(
            [{"deliverable": "multipactor-verification-plan", "maturity": "draft"}]
        )
        self.assertEqual(got, {"multipactor-verification-plan": "draft"})

    def test_none_means_nothing_was_submitted(self):
        self.assertEqual(logic.normalize_submissions(None), {})

    def test_unknown_data_item_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_submissions({"multipactor-poster": "draft"})

    def test_duplicate_submission_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_submissions(
                [
                    {"deliverable": "multipactor-test-report", "maturity": "draft"},
                    {"deliverable": "multipactor-test-report", "maturity": "approved"},
                ]
            )

    def test_missing_maturity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_submissions([{"deliverable": "multipactor-test-report"}])

    def test_missing_deliverable_key_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_submissions([{"maturity": "draft"}])

    def test_non_mapping_row_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_submissions(["multipactor-test-report"])

    def test_bad_maturity_in_submission_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_submissions({"multipactor-test-report": "signed"})


class GateAuditTests(unittest.TestCase):
    def test_complete_gate_is_compliant(self):
        result = logic.evaluate_gate(
            "cdr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
                "multipactor-test-procedure": "draft",
            },
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing"], ())
        self.assertEqual(result["immature"], ())

    def test_missing_item_is_reported(self):
        result = logic.evaluate_gate(
            "cdr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
            },
        )
        self.assertEqual(result["missing"], ("multipactor-test-procedure",))
        self.assertFalse(result["compliant"])

    def test_immature_item_is_reported_even_though_delivered(self):
        result = logic.evaluate_gate(
            "cdr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "issued",
                "multipactor-verification-plan": "approved",
                "multipactor-test-procedure": "draft",
            },
        )
        self.assertEqual(result["missing"], ())
        self.assertEqual(len(result["immature"]), 1)
        self.assertEqual(
            result["immature"][0]["deliverable"], "multipactor-critical-item-list"
        )
        self.assertFalse(result["compliant"])

    def test_over_mature_delivery_is_accepted(self):
        result = logic.evaluate_gate(
            "pdr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
            },
        )
        self.assertTrue(result["compliant"])

    def test_early_delivery_is_unplanned_not_missing(self):
        result = logic.evaluate_gate(
            "srr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "draft",
                "multipactor-verification-plan": "draft",
            },
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["unplanned"]), 1)
        self.assertEqual(result["unplanned"][0]["reason"], "not-yet-due")

    def test_item_from_an_undeclared_route_is_unplanned(self):
        result = logic.evaluate_gate(
            "cdr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
                "multipactor-test-procedure": "draft",
                "similarity-justification-dossier": "approved",
            },
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["unplanned"][0]["reason"], "route-not-declared")

    def test_unknown_gate_in_audit_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.evaluate_gate("orr", TEST_ROUTE, {})


class ReadinessTests(unittest.TestCase):
    def test_partial_gate_scores_a_fraction(self):
        result = logic.evaluate_gate(
            "cdr",
            TEST_ROUTE,
            {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
            },
        )
        self.assertAlmostEqual(logic.gate_readiness(result), 2.0 / 3.0, places=12)

    def test_gate_with_nothing_owed_is_vacuously_ready(self):
        result = {"expected": {}, "satisfied": ()}
        self.assertAlmostEqual(logic.gate_readiness(result), 1.0, places=12)

    def test_readiness_needs_an_evaluate_gate_result(self):
        with self.assertRaises(ValueError):
            logic.gate_readiness({"satisfied": ()})

    def test_threshold_absorbs_representation_error(self):
        drifted = 0.7 + 0.1
        self.assertLess(drifted, 0.8)
        self.assertTrue(logic.meets_readiness_threshold(drifted, 0.8))

    def test_genuine_shortfall_still_fails_the_threshold(self):
        self.assertFalse(logic.meets_readiness_threshold(0.75, 0.8))

    def test_score_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.meets_readiness_threshold(1.5, 1.0)

    def test_boolean_score_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.meets_readiness_threshold(True, 1.0)


class RollUpTests(unittest.TestCase):
    def _full_programme(self):
        return {
            "srr": {"multipactor-critical-item-list": "draft"},
            "pdr": {
                "multipactor-critical-item-list": "issued",
                "multipactor-verification-plan": "draft",
            },
            "cdr": {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
                "multipactor-test-procedure": "draft",
            },
            "qr": {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
                "multipactor-test-procedure": "approved",
                "multipactor-test-report": "approved",
                "multipactor-free-declaration": "draft",
            },
            "ar": {
                "multipactor-critical-item-list": "approved",
                "multipactor-verification-plan": "approved",
                "multipactor-test-procedure": "approved",
                "multipactor-test-report": "approved",
                "multipactor-free-declaration": "approved",
            },
        }

    def test_complete_programme_has_no_blocking_gate(self):
        roll = logic.roll_up_reviews(TEST_ROUTE, self._full_programme())
        self.assertIsNone(roll["blocking_gate"])
        self.assertTrue(roll["compliant"])
        self.assertEqual(len(roll["gates"]), 5)

    def test_first_shortfall_becomes_the_blocking_gate(self):
        programme = self._full_programme()
        del programme["cdr"]["multipactor-test-procedure"]
        roll = logic.roll_up_reviews(TEST_ROUTE, programme)
        self.assertEqual(roll["blocking_gate"], "cdr")
        self.assertFalse(roll["compliant"])

    def test_every_gate_carries_a_readiness_score(self):
        roll = logic.roll_up_reviews(TEST_ROUTE, self._full_programme())
        for gate in roll["gates"]:
            self.assertAlmostEqual(gate["readiness"], 1.0, places=12)
            self.assertTrue(gate["meets_threshold"])

    def test_non_mapping_programme_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.roll_up_reviews(TEST_ROUTE, [("cdr", {})])

    def test_unknown_gate_key_in_programme_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.roll_up_reviews(TEST_ROUTE, {"frr": {}})

    def test_empty_programme_blocks_at_the_first_gate(self):
        roll = logic.roll_up_reviews(TEST_ROUTE, {})
        self.assertEqual(roll["blocking_gate"], "srr")


if __name__ == "__main__":
    unittest.main()
