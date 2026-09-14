#!/usr/bin/env python3
"""Contract test for the coverglass test-role separation (offline)."""

import copy
import unittest

from e2008_coverglass_testing_overview_logic import (
    COATINGS,
    DEFAULT_TEST_POLICY,
    MANDATORY_TESTS_MISSING,
    PROGRAMMES,
    ROLES,
    ROLES_MISASSIGNED,
    ROLES_PARTIALLY_SEPARATED,
    ROLES_SEPARATED,
    TEST_CATALOGUE,
    assess_testing_overview,
    declared_programmes,
    destructive_specimen_demand,
    is_destructive,
    mandatory_tests,
    misassigned_tests,
    normalise_coatings,
    partition_tests,
    programme_coverage,
    sample_size,
    test_role,
    tests_permitted_in,
    testing_overview_index,
    validate_test_policy,
)


def _complete_assignments(coatings=()):
    assignments = {}
    for programme in PROGRAMMES:
        for test in mandatory_tests(programme, coatings):
            assignments.setdefault(test, []).append(programme)
    return {test: tuple(programmes) for test, programmes in assignments.items()}


BASE_CASE = {
    "assignments": _complete_assignments(),
    "coatings": [],
    "lot_size": 400,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_test_policy(DEFAULT_TEST_POLICY), DEFAULT_TEST_POLICY)

    def test_policy_weights_every_programme(self):
        for programme in PROGRAMMES:
            self.assertIn(programme, DEFAULT_TEST_POLICY["programme_weights"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_policy(["qualification"])

    def test_policy_missing_a_programme_weight_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_POLICY)
        del broken["programme_weights"]["procurement"]
        with self.assertRaises(ValueError):
            validate_test_policy(broken)

    def test_policy_with_inverted_sample_limits_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_POLICY)
        broken["max_lot_sample"] = 2
        with self.assertRaises(ValueError):
            validate_test_policy(broken)

    def test_policy_with_a_fractional_sample_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_TEST_POLICY)
        broken["min_lot_sample"] = 2.5
        with self.assertRaises(ValueError):
            validate_test_policy(broken)


class CatalogueTests(unittest.TestCase):
    def test_every_catalogue_entry_carries_a_known_role(self):
        for test in TEST_CATALOGUE:
            self.assertIn(test_role(test), ROLES)

    def test_an_endurance_run_is_qualification_only(self):
        self.assertEqual(
            test_role("coverglass-thermal-cycling-endurance"), "qualification-only"
        )

    def test_an_incoming_check_is_procurement_only(self):
        self.assertEqual(
            test_role("coverglass-incoming-batch-identity-check"), "procurement-only"
        )

    def test_a_dimensional_inspection_serves_both(self):
        self.assertEqual(test_role("coverglass-dimensional-inspection"), "both")

    def test_endurance_runs_are_destructive(self):
        self.assertTrue(is_destructive("coverglass-particle-irradiation-stability"))

    def test_a_visual_inspection_is_not_destructive(self):
        self.assertFalse(is_destructive("coverglass-visual-inspection"))

    def test_unknown_test_rejected(self):
        with self.assertRaises(ValueError):
            test_role("coverglass-vibe-check")

    def test_unknown_test_rejected_by_the_destructive_lookup(self):
        with self.assertRaises(ValueError):
            is_destructive("coverglass-vibe-check")


class PermittedTests(unittest.TestCase):
    def test_qualification_cannot_claim_a_procurement_only_test(self):
        self.assertNotIn(
            "coverglass-incoming-batch-identity-check",
            tests_permitted_in("qualification"),
        )

    def test_procurement_cannot_claim_a_qualification_only_test(self):
        self.assertNotIn(
            "coverglass-thermal-cycling-endurance", tests_permitted_in("procurement")
        )

    def test_dual_role_tests_appear_in_both_programmes(self):
        self.assertIn(
            "coverglass-spectral-transmittance", tests_permitted_in("qualification")
        )
        self.assertIn(
            "coverglass-spectral-transmittance", tests_permitted_in("procurement")
        )

    def test_unknown_programme_rejected(self):
        with self.assertRaises(ValueError):
            tests_permitted_in("marketing")


class MandatorySetTests(unittest.TestCase):
    def test_both_programmes_carry_a_mandatory_set(self):
        for programme in PROGRAMMES:
            self.assertTrue(mandatory_tests(programme))

    def test_a_conductive_coating_adds_a_conductivity_measurement(self):
        bare = mandatory_tests("procurement")
        coated = mandatory_tests("procurement", ["conductive-coating"])
        self.assertNotIn("coverglass-surface-conductivity-measurement", bare)
        self.assertIn("coverglass-surface-conductivity-measurement", coated)

    def test_a_uv_reflective_coating_only_binds_qualification(self):
        coated = mandatory_tests("procurement", ["uv-reflective-coating"])
        self.assertNotIn("coverglass-ultraviolet-irradiation-stability", coated)
        self.assertIn(
            "coverglass-ultraviolet-irradiation-stability",
            mandatory_tests("qualification", ["uv-reflective-coating"]),
        )

    def test_a_mandatory_set_never_contains_a_forbidden_test(self):
        for programme in PROGRAMMES:
            permitted = set(tests_permitted_in(programme))
            for test in mandatory_tests(programme, list(COATINGS)):
                self.assertIn(test, permitted)

    def test_unknown_coating_rejected(self):
        with self.assertRaises(ValueError):
            mandatory_tests("qualification", ["hand-polish"])


class CoatingStackTests(unittest.TestCase):
    def test_stack_is_deduplicated_and_ordered(self):
        self.assertEqual(
            normalise_coatings(
                ["conductive-coating", "antireflective-coating", "conductive-coating"]
            ),
            ("antireflective-coating", "conductive-coating"),
        )

    def test_bare_string_stack_rejected(self):
        with self.assertRaises(ValueError):
            normalise_coatings("conductive-coating")


class PartitionTests(unittest.TestCase):
    def test_a_mixed_set_is_grouped_by_role(self):
        grouped = partition_tests(
            [
                "coverglass-thermal-cycling-endurance",
                "coverglass-incoming-batch-identity-check",
                "coverglass-visual-inspection",
            ]
        )
        self.assertEqual(
            grouped["qualification-only"], ("coverglass-thermal-cycling-endurance",)
        )
        self.assertEqual(
            grouped["procurement-only"], ("coverglass-incoming-batch-identity-check",)
        )
        self.assertEqual(grouped["both"], ("coverglass-visual-inspection",))

    def test_an_empty_set_groups_to_three_empty_roles(self):
        grouped = partition_tests([])
        for role in ROLES:
            self.assertEqual(grouped[role], ())

    def test_duplicates_are_collapsed(self):
        grouped = partition_tests(
            ["coverglass-visual-inspection", "coverglass-visual-inspection"]
        )
        self.assertEqual(grouped["both"], ("coverglass-visual-inspection",))

    def test_unknown_test_in_a_set_rejected(self):
        with self.assertRaises(ValueError):
            partition_tests(["coverglass-tea-break"])


class BookingTests(unittest.TestCase):
    def test_a_single_programme_name_is_accepted(self):
        self.assertEqual(
            declared_programmes("coverglass-visual-inspection", "procurement"),
            ("procurement",),
        )

    def test_a_dual_booking_is_kept_in_catalogue_order(self):
        self.assertEqual(
            declared_programmes(
                "coverglass-visual-inspection", ["procurement", "qualification"]
            ),
            ("qualification", "procurement"),
        )

    def test_a_repeated_programme_is_collapsed(self):
        self.assertEqual(
            declared_programmes(
                "coverglass-visual-inspection", ("procurement", "procurement")
            ),
            ("procurement",),
        )

    def test_a_booking_to_no_programme_rejected(self):
        with self.assertRaises(ValueError):
            declared_programmes("coverglass-visual-inspection", [])

    def test_a_booking_on_an_unknown_test_rejected(self):
        with self.assertRaises(ValueError):
            declared_programmes("coverglass-taste-test", "procurement")


class MisassignmentTests(unittest.TestCase):
    def test_a_clean_booking_reports_nothing(self):
        self.assertEqual(misassigned_tests(BASE_CASE["assignments"]), ())

    def test_an_endurance_run_booked_to_procurement_is_caught(self):
        found = misassigned_tests(
            {"coverglass-thermal-cycling-endurance": "procurement"}
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["catalogue_role"], "qualification-only")

    def test_an_incoming_check_booked_to_qualification_is_caught(self):
        found = misassigned_tests(
            {"coverglass-incoming-batch-identity-check": "qualification"}
        )
        self.assertEqual(len(found), 1)

    def test_a_dual_role_test_is_never_misassigned(self):
        for programme in PROGRAMMES:
            self.assertEqual(
                misassigned_tests({"coverglass-visual-inspection": programme}), ()
            )

    def test_unknown_programme_in_a_booking_rejected(self):
        with self.assertRaises(ValueError):
            misassigned_tests({"coverglass-visual-inspection": "someday"})

    def test_non_mapping_assignments_rejected(self):
        with self.assertRaises(ValueError):
            misassigned_tests(["coverglass-visual-inspection"])


class CoverageTests(unittest.TestCase):
    def test_a_complete_booking_scores_one(self):
        for programme in PROGRAMMES:
            coverage = programme_coverage(programme, BASE_CASE["assignments"])
            self.assertAlmostEqual(coverage["fraction"], 1.0, places=9)
            self.assertEqual(coverage["missing"], ())

    def test_an_empty_booking_scores_zero(self):
        coverage = programme_coverage("procurement", {})
        self.assertAlmostEqual(coverage["fraction"], 0.0, places=9)
        self.assertTrue(coverage["missing"])

    def test_a_test_booked_to_the_other_programme_does_not_count(self):
        assignments = dict(BASE_CASE["assignments"])
        assignments["coverglass-visual-inspection"] = ("qualification",)
        coverage = programme_coverage("procurement", assignments)
        self.assertIn("coverglass-visual-inspection", coverage["missing"])

    def test_a_coating_raises_the_bar_for_procurement(self):
        assignments = dict(BASE_CASE["assignments"])
        coverage = programme_coverage(
            "procurement", assignments, ["conductive-coating"]
        )
        self.assertIn("coverglass-surface-conductivity-measurement", coverage["missing"])

    def test_non_mapping_assignments_rejected(self):
        with self.assertRaises(ValueError):
            programme_coverage("procurement", ())


class SampleSizeTests(unittest.TestCase):
    def test_a_small_lot_still_gives_the_floor(self):
        self.assertEqual(sample_size(50), 5)

    def test_a_large_lot_draws_the_declared_fraction(self):
        self.assertEqual(sample_size(1000), 20)

    def test_the_draw_is_capped(self):
        self.assertEqual(sample_size(100000), 50)

    def test_the_draw_never_exceeds_the_lot(self):
        self.assertEqual(sample_size(3), 3)

    def test_a_fractional_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(400.5)

    def test_a_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(0)


class SpecimenDemandTests(unittest.TestCase):
    def test_a_non_destructive_procurement_set_needs_no_over_build(self):
        demand = destructive_specimen_demand(BASE_CASE["assignments"], 400)
        self.assertFalse(demand["over_build_required"])
        self.assertEqual(demand["specimens_consumed"], 0)

    def test_a_destructive_procurement_test_consumes_a_draw(self):
        assignments = dict(BASE_CASE["assignments"])
        assignments["coverglass-coating-adhesion-test"] = (
            "qualification",
            "procurement",
        )
        demand = destructive_specimen_demand(assignments, 1000)
        self.assertTrue(demand["over_build_required"])
        self.assertEqual(demand["specimens_consumed"], 20)

    def test_qualification_side_destruction_does_not_hit_the_lot(self):
        demand = destructive_specimen_demand(
            {"coverglass-thermal-cycling-endurance": "qualification"}, 1000
        )
        self.assertEqual(demand["destructive_tests"], ())

    def test_non_mapping_assignments_rejected(self):
        with self.assertRaises(ValueError):
            destructive_specimen_demand([], 400)


class OverviewIndexTests(unittest.TestCase):
    def test_both_programmes_complete_gives_one(self):
        coverage = {p: {"fraction": 1.0} for p in PROGRAMMES}
        self.assertAlmostEqual(testing_overview_index(coverage), 1.0, places=9)

    def test_one_programme_empty_gives_a_half(self):
        coverage = {"qualification": {"fraction": 1.0}, "procurement": {"fraction": 0.0}}
        self.assertAlmostEqual(testing_overview_index(coverage), 0.5, places=9)

    def test_weights_are_honoured(self):
        policy = copy.deepcopy(DEFAULT_TEST_POLICY)
        policy["programme_weights"] = {"qualification": 0.75, "procurement": 0.25}
        coverage = {"qualification": {"fraction": 1.0}, "procurement": {"fraction": 0.0}}
        self.assertAlmostEqual(
            testing_overview_index(coverage, policy), 0.75, places=9
        )

    def test_an_out_of_range_fraction_rejected(self):
        with self.assertRaises(ValueError):
            testing_overview_index({"qualification": {"fraction": -0.1}})

    def test_unknown_programme_in_coverage_rejected(self):
        with self.assertRaises(ValueError):
            testing_overview_index({"logistics": {"fraction": 1.0}})


class AssessmentTests(unittest.TestCase):
    def test_a_clean_programme_separates_the_roles(self):
        result = assess_testing_overview(BASE_CASE)
        self.assertEqual(result["verdict"], ROLES_SEPARATED)
        self.assertAlmostEqual(result["overview_index"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_misassigned_test_dominates_the_verdict(self):
        assignments = dict(BASE_CASE["assignments"])
        assignments["coverglass-incoming-batch-identity-check"] = (
            "procurement",
            "qualification",
        )
        result = assess_testing_overview(_case(BASE_CASE, assignments=assignments))
        self.assertEqual(result["verdict"], ROLES_MISASSIGNED)
        self.assertTrue(result["misassigned"])

    def test_an_empty_programme_leaves_the_mandatory_sets_missing(self):
        result = assess_testing_overview(_case(BASE_CASE, assignments={}))
        self.assertEqual(result["verdict"], MANDATORY_TESTS_MISSING)
        self.assertAlmostEqual(result["overview_index"], 0.0, places=9)

    def test_one_gap_reads_as_partial_separation(self):
        assignments = dict(BASE_CASE["assignments"])
        del assignments["coverglass-lot-sample-verification"]
        result = assess_testing_overview(_case(BASE_CASE, assignments=assignments))
        self.assertEqual(result["verdict"], ROLES_PARTIALLY_SEPARATED)
        self.assertTrue(any("procurement programme" in f for f in result["findings"]))

    def test_an_index_exactly_on_the_floor_still_reads_partial(self):
        policy = copy.deepcopy(DEFAULT_TEST_POLICY)
        policy["partial_index_floor"] = 0.5
        assignments = {
            test: ("qualification",) for test in mandatory_tests("qualification")
        }
        result = assess_testing_overview(
            _case(BASE_CASE, assignments=assignments), policy
        )
        self.assertAlmostEqual(result["overview_index"], 0.5, places=9)
        self.assertEqual(result["verdict"], ROLES_PARTIALLY_SEPARATED)

    def test_a_coating_reopens_a_complete_programme(self):
        result = assess_testing_overview(
            _case(BASE_CASE, coatings=["conductive-coating"])
        )
        self.assertNotEqual(result["verdict"], ROLES_SEPARATED)

    def test_a_coating_driven_programme_can_be_completed(self):
        coatings = ["conductive-coating"]
        result = assess_testing_overview(
            _case(
                BASE_CASE,
                coatings=coatings,
                assignments=_complete_assignments(coatings),
            )
        )
        self.assertEqual(result["verdict"], ROLES_SEPARATED)

    def test_a_destructive_lot_test_is_reported_as_an_over_build(self):
        assignments = dict(BASE_CASE["assignments"])
        assignments["coverglass-coating-adhesion-test"] = (
            "qualification",
            "procurement",
        )
        result = assess_testing_overview(
            _case(BASE_CASE, assignments=assignments, lot_size=1000)
        )
        self.assertTrue(result["specimen_demand"]["over_build_required"])
        self.assertTrue(any("over-built" in f for f in result["findings"]))

    def test_the_grouped_view_is_reported(self):
        result = assess_testing_overview(BASE_CASE)
        for role in ROLES:
            self.assertIn(role, result["grouped_tests"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_testing_overview("qualification")

    def test_case_without_assignments_rejected(self):
        with self.assertRaises(ValueError):
            assess_testing_overview({"coatings": [], "lot_size": 400})

    def test_case_with_a_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_testing_overview(_case(BASE_CASE, lot_size=0))

    def test_case_with_an_unknown_test_rejected(self):
        assignments = dict(BASE_CASE["assignments"])
        assignments["coverglass-taste-test"] = ("procurement",)
        with self.assertRaises(ValueError):
            assess_testing_overview(_case(BASE_CASE, assignments=assignments))


if __name__ == "__main__":
    unittest.main()
