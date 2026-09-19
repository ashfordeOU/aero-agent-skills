"""Contract tests for the clause 4.1 device need-derivation logic."""

import unittest

from e2040_device_development_lifecycle_overview_logic import (
    MANDATORY_CATEGORIES,
    MATURITY_LEVELS,
    NEED_CATEGORIES,
    PHASE_SEQUENCE,
    assess_lifecycle_derivation,
    build_need_index,
    category_coverage,
    derivation_chain,
    maturity_by_phase,
    maturity_index,
    needs_by_category,
    needs_by_phase,
    normalize_category,
    normalize_maturity,
    normalize_phase,
    phase_index,
    validate_need,
)


def base_needs():
    return [
        {
            "id": "SYS-F-01",
            "category": "functional",
            "phase": "phase-a",
            "maturity": "stated",
            "parent": None,
            "title": "provide regulated power to the payload",
        },
        {
            "id": "DEV-F-01",
            "category": "functional",
            "phase": "phase-b",
            "maturity": "derived",
            "parent": "SYS-F-01",
        },
        {
            "id": "DEV-F-02",
            "category": "functional",
            "phase": "phase-c",
            "maturity": "specified",
            "parent": "DEV-F-01",
        },
        {
            "id": "DEV-P-01",
            "category": "performance",
            "phase": "phase-b",
            "maturity": "budgeted",
            "parent": "SYS-F-01",
        },
        {
            "id": "DEV-P-02",
            "category": "performance",
            "phase": "phase-c",
            "maturity": "specified",
            "parent": "DEV-P-01",
        },
        {
            "id": "DEV-E-01",
            "category": "environmental",
            "phase": "phase-b",
            "maturity": "derived",
            "parent": "SYS-F-01",
        },
        {
            "id": "DEV-E-02",
            "category": "environmental",
            "phase": "phase-c",
            "maturity": "specified",
            "parent": "DEV-E-01",
        },
    ]


class PhaseTests(unittest.TestCase):
    def test_canonical_phase_passes_through(self):
        self.assertEqual(normalize_phase("phase-c"), "phase-c")

    def test_bare_letter_is_folded(self):
        self.assertEqual(normalize_phase("B"), "phase-b")

    def test_spaced_spelling_is_folded(self):
        self.assertEqual(normalize_phase("Phase D"), "phase-d")

    def test_named_phase_is_folded(self):
        self.assertEqual(normalize_phase("feasibility"), "phase-a")

    def test_phase_order_is_increasing(self):
        self.assertLess(phase_index("phase-a"), phase_index("phase-d"))

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("phase-z")

    def test_blank_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("   ")

    def test_non_string_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase(3)


class CategoryAndMaturityTests(unittest.TestCase):
    def test_mandatory_categories_are_in_the_full_set(self):
        for category in MANDATORY_CATEGORIES:
            self.assertIn(category, NEED_CATEGORIES)

    def test_environment_folds_to_environmental(self):
        self.assertEqual(normalize_category("Environment"), "environmental")

    def test_perf_folds_to_performance(self):
        self.assertEqual(normalize_category("perf"), "performance")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("aesthetic")

    def test_maturity_order_is_increasing(self):
        self.assertLess(maturity_index("stated"), maturity_index("verified"))

    def test_maturity_levels_are_unique(self):
        self.assertEqual(len(set(MATURITY_LEVELS)), len(MATURITY_LEVELS))

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_maturity("nearly")


class NeedValidationTests(unittest.TestCase):
    def test_need_is_folded_onto_canonical_tokens(self):
        need = validate_need(
            {"id": " DEV-1 ", "category": "Env", "phase": "C", "maturity": "Derived"}
        )
        self.assertEqual(need["id"], "DEV-1")
        self.assertEqual(need["category"], "environmental")
        self.assertEqual(need["phase"], "phase-c")

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_need({"id": "DEV-1", "category": "functional", "phase": "phase-b"})

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(
                {"id": " ", "category": "functional", "phase": "phase-b",
                 "maturity": "derived"}
            )

    def test_self_parent_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(
                {"id": "DEV-1", "category": "functional", "phase": "phase-b",
                 "maturity": "derived", "parent": "DEV-1"}
            )

    def test_non_mapping_need_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(["DEV-1"])

    def test_duplicate_identifier_rejected(self):
        needs = base_needs()
        needs.append(dict(needs[1]))
        with self.assertRaises(ValueError):
            build_need_index(needs)

    def test_index_holds_every_need(self):
        self.assertEqual(len(build_need_index(base_needs())), 7)


class ChainTests(unittest.TestCase):
    def test_chain_reaches_the_root(self):
        index = build_need_index(base_needs())
        chain = derivation_chain(index, "DEV-F-02")
        self.assertEqual([n["id"] for n in chain], ["DEV-F-02", "DEV-F-01", "SYS-F-01"])

    def test_root_chain_is_one_long(self):
        index = build_need_index(base_needs())
        self.assertEqual(len(derivation_chain(index, "SYS-F-01")), 1)

    def test_unknown_need_rejected(self):
        index = build_need_index(base_needs())
        with self.assertRaises(ValueError):
            derivation_chain(index, "NOPE")

    def test_missing_parent_is_reported(self):
        needs = base_needs()
        needs[1]["parent"] = "GHOST"
        index = build_need_index(needs)
        with self.assertRaises(ValueError):
            derivation_chain(index, "DEV-F-01")

    def test_circular_derivation_is_reported(self):
        needs = base_needs()
        needs[0]["parent"] = "DEV-F-02"
        index = build_need_index(needs)
        with self.assertRaises(ValueError):
            derivation_chain(index, "DEV-F-01")


class GroupingTests(unittest.TestCase):
    def test_grouping_by_phase_covers_every_phase_key(self):
        grouped = needs_by_phase(build_need_index(base_needs()))
        self.assertEqual(set(grouped), set(PHASE_SEQUENCE))

    def test_phase_b_holds_three_needs(self):
        grouped = needs_by_phase(build_need_index(base_needs()))
        self.assertEqual(len(grouped["phase-b"]), 3)

    def test_grouping_by_category_is_sorted(self):
        grouped = needs_by_category(build_need_index(base_needs()))
        self.assertEqual(grouped["performance"], ["DEV-P-01", "DEV-P-02"])

    def test_full_coverage_reports_nothing_missing(self):
        coverage = category_coverage(build_need_index(base_needs()))
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing_mandatory"], [])

    def test_missing_category_is_named(self):
        needs = [n for n in base_needs() if n["category"] != "environmental"]
        coverage = category_coverage(build_need_index(needs))
        self.assertEqual(coverage["missing_mandatory"], ["environmental"])

    def test_maturity_table_records_the_highest_level_per_phase(self):
        table = maturity_by_phase(build_need_index(base_needs()))
        self.assertEqual(table["functional"]["phase-c"], maturity_index("specified"))


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"needs": base_needs()}
        spec.update(overrides)
        return spec

    def test_well_formed_derivation_is_compliant(self):
        result = assess_lifecycle_derivation(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_orphan_need_is_flagged(self):
        needs = base_needs()
        needs[2]["parent"] = "GHOST"
        result = assess_lifecycle_derivation(self._spec(needs=needs))
        self.assertEqual(result["orphans"], ["DEV-F-02"])
        self.assertFalse(result["compliant"])

    def test_need_derived_before_its_parent_is_flagged(self):
        needs = base_needs()
        needs[1]["phase"] = "phase-0"
        result = assess_lifecycle_derivation(self._spec(needs=needs))
        self.assertIn("DEV-F-01", result["derived_before_parent"])

    def test_circular_derivation_is_flagged(self):
        needs = base_needs()
        needs[0]["parent"] = "DEV-F-02"
        result = assess_lifecycle_derivation(self._spec(needs=needs))
        self.assertTrue(result["circular"])
        self.assertFalse(result["compliant"])

    def test_missing_mandatory_category_is_flagged(self):
        needs = [n for n in base_needs() if n["category"] != "performance"]
        result = assess_lifecycle_derivation(self._spec(needs=needs))
        self.assertTrue(any("no performance need" in f for f in result["findings"]))

    def test_maturity_regression_is_flagged(self):
        needs = base_needs()
        needs[2]["maturity"] = "stated"
        result = assess_lifecycle_derivation(self._spec(needs=needs))
        self.assertTrue(result["maturity_regressions"])

    def test_phase_gate_shortfall_is_flagged(self):
        result = assess_lifecycle_derivation(
            self._spec(required_maturity_at_phase={"phase-b": "specified"})
        )
        self.assertTrue(result["gate_shortfalls"])
        self.assertFalse(result["compliant"])

    def test_phase_gate_met_leaves_it_compliant(self):
        result = assess_lifecycle_derivation(
            self._spec(required_maturity_at_phase={"phase-c": "specified"})
        )
        self.assertEqual(result["gate_shortfalls"], [])
        self.assertTrue(result["compliant"])

    def test_empty_need_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifecycle_derivation({"needs": []})

    def test_missing_needs_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifecycle_derivation({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifecycle_derivation(["needs"])

    def test_non_mapping_gate_rejected(self):
        with self.assertRaises(ValueError):
            assess_lifecycle_derivation(
                self._spec(required_maturity_at_phase=["phase-b"])
            )

    def test_result_reports_the_grouped_views(self):
        result = assess_lifecycle_derivation(self._spec())
        self.assertEqual(set(result["by_phase"]), set(PHASE_SEQUENCE))
        self.assertEqual(sorted(result["by_category"]), sorted(MANDATORY_CATEGORIES))


if __name__ == "__main__":
    unittest.main()
