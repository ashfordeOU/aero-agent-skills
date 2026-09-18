#!/usr/bin/env python3
"""Contract test for the Annex A applicability-tables leaf."""

import unittest

from q2030_applicability_tables_logic import (
    assess_applicability,
    coverage_fraction,
    lookup_disposition,
    make_row,
    normalize_disposition,
    normalize_token,
    reconcile_with_normative,
    resolve_applicability,
    undetermined_sets,
    validate_table,
)

UNIVERSE = ["crimping", "sleeving", "labelling", "branching", "emc-foil"]


def table():
    return [
        {"harness_type": "low-frequency bundle", "category": "2", "requirement_set": "crimping",
         "disposition": "A"},
        {"harness_type": "low-frequency bundle", "category": "2", "requirement_set": "sleeving",
         "disposition": "A"},
        {"harness_type": "low-frequency bundle", "category": "2", "requirement_set": "labelling",
         "disposition": "A"},
        {"harness_type": "low-frequency bundle", "category": "2", "requirement_set": "branching",
         "disposition": "conditional", "condition": "bundle-is-braid-shielded"},
        {"harness_type": "low-frequency bundle", "category": "2", "requirement_set": "emc-foil",
         "disposition": "NA"},
        {"harness_type": "coaxial assembly", "category": "2", "requirement_set": "crimping",
         "disposition": "A"},
    ]


class TestNormalizeToken(unittest.TestCase):
    def test_spaces_fold_to_hyphens(self):
        self.assertEqual(normalize_token("low frequency bundle"), "low-frequency-bundle")

    def test_case_is_folded(self):
        self.assertEqual(normalize_token("EMC-Foil"), "emc-foil")

    def test_repeated_separators_collapse(self):
        self.assertEqual(normalize_token("emc  foil"), "emc-foil")

    def test_blank_token_raises(self):
        with self.assertRaises(ValueError):
            normalize_token("   ")

    def test_non_string_token_raises(self):
        with self.assertRaises(ValueError):
            normalize_token(2)


class TestNormalizeDisposition(unittest.TestCase):
    def test_applicable_survives(self):
        self.assertEqual(normalize_disposition("applicable"), "applicable")

    def test_single_letter_a_folds_to_applicable(self):
        self.assertEqual(normalize_disposition("A"), "applicable")

    def test_na_folds_to_not_applicable(self):
        self.assertEqual(normalize_disposition("NA"), "not-applicable")

    def test_tailorable_folds_to_conditional(self):
        self.assertEqual(normalize_disposition("tailorable"), "conditional")

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            normalize_disposition("maybe")


class TestMakeRow(unittest.TestCase):
    def test_applicable_row_carries_no_condition(self):
        row = make_row("low frequency bundle", "2", "crimping", "A")
        self.assertIsNone(row["condition"])

    def test_conditional_row_keeps_its_condition(self):
        row = make_row("bundle", "2", "branching", "C", "bundle-is-braid-shielded")
        self.assertEqual(row["condition"], "bundle-is-braid-shielded")

    def test_conditional_row_without_a_condition_raises(self):
        with self.assertRaises(ValueError):
            make_row("bundle", "2", "branching", "conditional")

    def test_applicable_row_with_a_condition_raises(self):
        with self.assertRaises(ValueError):
            make_row("bundle", "2", "crimping", "A", "some-condition")

    def test_row_keys_are_normalized(self):
        row = make_row(" Bundle ", "2", "EMC Foil", "na")
        self.assertEqual(row["requirement_set"], "emc-foil")


class TestValidateTable(unittest.TestCase):
    def test_sound_table_normalizes(self):
        self.assertEqual(len(validate_table(table())), 6)

    def test_repeated_address_raises(self):
        rows = table()
        rows.append({"harness_type": "low-frequency bundle", "category": "2",
                     "requirement_set": "crimping", "disposition": "NA"})
        with self.assertRaises(ValueError):
            validate_table(rows)

    def test_repeated_address_raises_even_when_it_agrees(self):
        rows = table()
        rows.append({"harness_type": "low-frequency bundle", "category": "2",
                     "requirement_set": "crimping", "disposition": "A"})
        with self.assertRaises(ValueError):
            validate_table(rows)

    def test_missing_row_key_raises(self):
        rows = table()
        del rows[0]["disposition"]
        with self.assertRaises(ValueError):
            validate_table(rows)

    def test_empty_table_raises(self):
        with self.assertRaises(ValueError):
            validate_table([])

    def test_non_mapping_row_raises(self):
        with self.assertRaises(ValueError):
            validate_table(["crimping"])


class TestLookup(unittest.TestCase):
    def test_addressed_set_is_found(self):
        rows = validate_table(table())
        self.assertEqual(
            lookup_disposition(rows, "low frequency bundle", "2", "crimping")["disposition"],
            "applicable",
        )

    def test_unaddressed_set_returns_none(self):
        rows = validate_table(table())
        self.assertIsNone(lookup_disposition(rows, "coaxial assembly", "2", "sleeving"))

    def test_lookup_is_insensitive_to_spelling(self):
        rows = validate_table(table())
        self.assertIsNotNone(lookup_disposition(rows, "LOW_FREQUENCY_BUNDLE", "2", "CRIMPING"))


class TestResolveApplicability(unittest.TestCase):
    def test_applicable_sets_are_grouped(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        self.assertEqual(resolution["applicable"], ["crimping", "labelling", "sleeving"])

    def test_excluded_sets_are_grouped(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        self.assertEqual(resolution["excluded"], ["emc-foil"])

    def test_undecided_condition_leaves_the_set_unresolved(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        self.assertEqual(resolution["unresolved"][0]["requirement_set"], "branching")

    def test_a_true_condition_makes_the_set_applicable(self):
        resolution = resolve_applicability(
            table(), "low frequency bundle", "2", {"bundle-is-braid-shielded": True}
        )
        self.assertIn("branching", resolution["applicable"])
        self.assertEqual(resolution["unresolved"], [])

    def test_a_false_condition_excludes_the_set(self):
        resolution = resolve_applicability(
            table(), "low frequency bundle", "2", {"bundle-is-braid-shielded": False}
        )
        self.assertIn("branching", resolution["excluded"])

    def test_another_pair_sees_only_its_own_rows(self):
        resolution = resolve_applicability(table(), "coaxial assembly", "2")
        self.assertEqual(resolution["applicable"], ["crimping"])

    def test_a_non_boolean_condition_decision_raises(self):
        with self.assertRaises(ValueError):
            resolve_applicability(table(), "low frequency bundle", "2",
                                  {"bundle-is-braid-shielded": "yes"})

    def test_a_pair_with_no_rows_resolves_to_nothing(self):
        resolution = resolve_applicability(table(), "flat flexible", "2")
        self.assertEqual(resolution["applicable"], [])
        self.assertEqual(resolution["excluded"], [])


class TestUndeterminedSets(unittest.TestCase):
    def test_a_fully_addressed_pair_has_nothing_undetermined(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        self.assertEqual(undetermined_sets(resolution, UNIVERSE), [])

    def test_unaddressed_sets_are_reported(self):
        resolution = resolve_applicability(table(), "coaxial assembly", "2")
        self.assertEqual(
            undetermined_sets(resolution, UNIVERSE),
            ["branching", "emc-foil", "labelling", "sleeving"],
        )

    def test_an_unresolved_conditional_set_counts_as_addressed(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        self.assertNotIn("branching", undetermined_sets(resolution, UNIVERSE))

    def test_empty_universe_raises(self):
        resolution = resolve_applicability(table(), "coaxial assembly", "2")
        with self.assertRaises(ValueError):
            undetermined_sets(resolution, [])


class TestReconcileWithNormative(unittest.TestCase):
    def test_a_normative_invocation_overrides_an_informative_exclusion(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        reconciliation = reconcile_with_normative(resolution, ["emc-foil"])
        self.assertEqual(reconciliation["invoked_but_excluded"], ["emc-foil"])
        self.assertIn("emc-foil", reconciliation["governing_applicable"])

    def test_a_normative_invocation_of_an_open_condition_is_reported(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        reconciliation = reconcile_with_normative(resolution, ["branching"])
        self.assertEqual(reconciliation["invoked_and_unresolved"], ["branching"])

    def test_no_invocation_leaves_the_table_result_alone(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        reconciliation = reconcile_with_normative(resolution, [])
        self.assertEqual(reconciliation["invoked_but_excluded"], [])
        self.assertEqual(reconciliation["governing_applicable"], resolution["applicable"])

    def test_non_sequence_invocation_raises(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        with self.assertRaises(ValueError):
            reconcile_with_normative(resolution, "emc-foil-set")


class TestCoverageFraction(unittest.TestCase):
    def test_four_of_five_sets_decided(self):
        resolution = resolve_applicability(table(), "low frequency bundle", "2")
        self.assertAlmostEqual(coverage_fraction(resolution, UNIVERSE), 0.8, places=9)

    def test_deciding_the_condition_completes_the_coverage(self):
        resolution = resolve_applicability(
            table(), "low frequency bundle", "2", {"bundle-is-braid-shielded": True}
        )
        self.assertAlmostEqual(coverage_fraction(resolution, UNIVERSE), 1.0, places=9)

    def test_a_sparse_pair_has_low_coverage(self):
        resolution = resolve_applicability(table(), "coaxial assembly", "2")
        self.assertAlmostEqual(coverage_fraction(resolution, UNIVERSE), 0.2, places=9)

    def test_empty_universe_raises(self):
        resolution = resolve_applicability(table(), "coaxial assembly", "2")
        with self.assertRaises(ValueError):
            coverage_fraction(resolution, [])


class TestAssessApplicability(unittest.TestCase):
    def test_a_fully_decided_pair_reports_decided(self):
        report = assess_applicability(
            {
                "table": table(),
                "harness_type": "low frequency bundle",
                "category": "2",
                "universe": UNIVERSE,
                "conditions": {"bundle-is-braid-shielded": True},
            }
        )
        self.assertTrue(report["decided"])
        self.assertEqual(report["findings"], [])

    def test_an_open_condition_is_a_finding(self):
        report = assess_applicability(
            {"table": table(), "harness_type": "low frequency bundle", "category": "2",
             "universe": UNIVERSE}
        )
        self.assertFalse(report["decided"])

    def test_an_unaddressed_set_is_a_finding_not_an_exclusion(self):
        report = assess_applicability(
            {"table": table(), "harness_type": "coaxial assembly", "category": "2",
             "universe": UNIVERSE}
        )
        self.assertIn("sleeving", report["undetermined"])
        self.assertNotIn("sleeving", report["resolution"]["excluded"])

    def test_a_normative_invocation_against_an_exclusion_is_a_finding(self):
        report = assess_applicability(
            {
                "table": table(),
                "harness_type": "low frequency bundle",
                "category": "2",
                "universe": UNIVERSE,
                "conditions": {"bundle-is-braid-shielded": True},
                "normative_invoked": ["emc-foil"],
            }
        )
        self.assertFalse(report["decided"])
        self.assertIn("emc-foil", report["reconciliation"]["governing_applicable"])

    def test_coverage_is_carried_up(self):
        report = assess_applicability(
            {"table": table(), "harness_type": "low frequency bundle", "category": "2",
             "universe": UNIVERSE, "conditions": {"bundle-is-braid-shielded": False}}
        )
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_applicability({"table": table(), "harness_type": "bundle", "category": "2"})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_applicability(["table"])

    def test_a_contradictory_table_raises_before_resolution(self):
        rows = table()
        rows.append({"harness_type": "low-frequency bundle", "category": "2",
                     "requirement_set": "sleeving", "disposition": "NA"})
        with self.assertRaises(ValueError):
            assess_applicability(
                {"table": rows, "harness_type": "low frequency bundle", "category": "2",
                 "universe": UNIVERSE}
            )


if __name__ == "__main__":
    unittest.main()
