"""Contract test for ica_cmr_ali_classification logic (stdlib unittest).

Offline, deterministic, no network. Run from the repo root:

    python3 skills/systems-engineering-safety/continued-airworthiness/\
        ica-cmr-ali-classification/scripts/test_ica_cmr_ali_classification.py

Covers the wave-36 spec contract: the classification truth table per
driver, ValueError rejection of unknown drivers and non-positive
intervals, the worked-example ALS coverage 0.6667 within 1e-4 with class
counts (ALI 2, CMR 1, routine 1), compliant and non-compliant interval
cases, the canonical-name ValueError, the counts-sum and
coverage = matched / required identities, determinism, and exact
documented dict keys.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ica_cmr_ali_classification_logic as logic

WORKED_EXAMPLE = [
    ("APU shaft LLP", "LLP", 18000),
    ("wing spar DT inspection", "DT", 4500),
    ("cabin interior check", "ROUTINE", 2000),
    ("hydraulic pump CMR", "CMR", 3000),
]


class ClassifyItemTests(unittest.TestCase):
    """Classification truth table: each driver maps to its expected kind."""

    def test_classify_llp_driver_is_ali(self):
        self.assertEqual(
            logic.classify_item("APU shaft LLP", "LLP", 18000)["kind"], "ALI")

    def test_classify_dt_driver_is_ali(self):
        self.assertEqual(
            logic.classify_item("wing spar DT inspection", "DT", 4500)["kind"],
            "ALI")

    def test_classify_ff_driver_is_ali(self):
        self.assertEqual(
            logic.classify_item("fuel-tank flammability check", "FF",
                                12000)["kind"], "ALI")

    def test_classify_cmr_driver_is_cmr(self):
        self.assertEqual(
            logic.classify_item("hydraulic pump CMR", "CMR", 3000)["kind"],
            "CMR")

    def test_classify_routine_driver_is_routine(self):
        self.assertEqual(
            logic.classify_item("cabin interior check", "ROUTINE", 2000)[
                "kind"], "routine")

    def test_classify_unknown_driver_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.classify_item("any item", "MSG3", 1000)

    def test_classify_negative_interval_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.classify_item("APU shaft LLP", "LLP", -5)

    def test_classify_zero_interval_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.classify_item("cabin interior check", "ROUTINE", 0)

    def test_classify_dict_keys_exact(self):
        keys = list(logic.classify_item("APU shaft LLP", "LLP", 18000).keys())
        self.assertEqual(keys, ["name", "driver", "kind", "rationale"])

    def test_classify_name_and_driver_passthrough(self):
        result = logic.classify_item("hydraulic pump CMR", "CMR", 3000)
        self.assertEqual(result["name"], "hydraulic pump CMR")
        self.assertEqual(result["driver"], "CMR")


class AlsCoverageTests(unittest.TestCase):
    """ALS coverage: matched canonical items over the canonical total."""

    def test_als_coverage_worked_example_two_of_three(self):
        coverage = logic.als_coverage(WORKED_EXAMPLE)
        self.assertEqual(coverage["matched"], 2)
        self.assertEqual(coverage["required"], 3)
        self.assertAlmostEqual(coverage["coverage_fraction"], 0.6667,
                               delta=1e-4)

    def test_als_coverage_full_program_is_one(self):
        full = WORKED_EXAMPLE + [("fuel-tank flammability check", "FF", 9000)]
        self.assertEqual(logic.als_coverage(full)["coverage_fraction"], 1.0)

    def test_als_coverage_empty_items_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.als_coverage([])

    def test_als_coverage_required_is_canonical_count(self):
        self.assertEqual(logic.als_coverage(WORKED_EXAMPLE)["required"],
                         len(logic.ALS_MAX_INTERVALS))

    def test_als_coverage_matched_counts_canonical_presence_only(self):
        # Non-canonical items never count toward matched; a repeated
        # canonical name counts once.
        items = [("APU shaft LLP", "LLP", 18000),
                 ("APU shaft LLP", "LLP", 9000),
                 ("cabin interior check", "ROUTINE", 2000)]
        self.assertEqual(logic.als_coverage(items)["matched"], 1)

    def test_als_coverage_dict_keys_exact(self):
        self.assertEqual(list(logic.als_coverage(WORKED_EXAMPLE).keys()),
                         ["matched", "required", "coverage_fraction"])


class IntervalComplianceTests(unittest.TestCase):
    """Per-item interval compliance against the ALS maximum intervals."""

    def test_interval_compliance_at_or_under_max_is_compliant(self):
        self.assertTrue(
            logic.interval_compliance("APU shaft LLP", 18000)["compliant"])
        self.assertTrue(
            logic.interval_compliance("APU shaft LLP", 20000.0)["compliant"])

    def test_interval_compliance_over_max_is_not_compliant(self):
        result = logic.interval_compliance("wing spar DT inspection", 4500)
        self.assertFalse(result["compliant"])

    def test_interval_compliance_unknown_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.interval_compliance("cabin interior check", 2000)

    def test_interval_compliance_nonpositive_interval_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.interval_compliance("APU shaft LLP", 0)
        with self.assertRaises(ValueError):
            logic.interval_compliance("APU shaft LLP", -100)

    def test_interval_compliance_dict_keys_exact(self):
        result = logic.interval_compliance("APU shaft LLP", 18000)
        self.assertEqual(list(result.keys()),
                         ["name", "max_interval", "compliant"])
        self.assertEqual(result["max_interval"], 20000.0)


class IcaCmrAliReviewTests(unittest.TestCase):
    """Whole-program review: counts, coverage, non-compliant, missing."""

    def test_review_class_counts_worked_example(self):
        counts = logic.ica_cmr_ali_review(WORKED_EXAMPLE)["class_counts"]
        self.assertEqual(counts, {"ALI": 2, "CMR": 1, "routine": 1})

    def test_review_class_counts_sum_to_item_count(self):
        counts = logic.ica_cmr_ali_review(WORKED_EXAMPLE)["class_counts"]
        self.assertEqual(sum(counts.values()), len(WORKED_EXAMPLE))

    def test_review_coverage_worked_example_matches_als_coverage(self):
        result = logic.ica_cmr_ali_review(WORKED_EXAMPLE)
        self.assertEqual(result["coverage"],
                         logic.als_coverage(WORKED_EXAMPLE))
        self.assertAlmostEqual(result["coverage"]["coverage_fraction"],
                               0.6667, delta=1e-4)

    def test_review_non_compliant_list_worked_example(self):
        result = logic.ica_cmr_ali_review(WORKED_EXAMPLE)
        self.assertEqual(result["non_compliant"], ["wing spar DT inspection"])

    def test_review_missing_als_items_worked_example(self):
        result = logic.ica_cmr_ali_review(WORKED_EXAMPLE)
        self.assertEqual(result["missing_als_items"],
                         ["fuel-tank flammability check"])

    def test_review_per_item_kind_sequence_in_program_order(self):
        result = logic.ica_cmr_ali_review(WORKED_EXAMPLE)
        kinds = [entry["kind"] for entry in result["per_item"]]
        self.assertEqual(kinds, ["ALI", "ALI", "routine", "CMR"])
        names = [entry["name"] for entry in result["per_item"]]
        self.assertEqual(names, [item[0] for item in WORKED_EXAMPLE])

    def test_review_full_complying_program_clean(self):
        # Every canonical item present with an interval at or under its
        # ALS maximum, so no violations and no missing items.
        full = [("APU shaft LLP", "LLP", 18000),
                ("wing spar DT inspection", "DT", 3500),
                ("fuel-tank flammability check", "FF", 9000),
                ("cabin interior check", "ROUTINE", 2000),
                ("hydraulic pump CMR", "CMR", 3000)]
        result = logic.ica_cmr_ali_review(full)
        self.assertEqual(result["non_compliant"], [])
        self.assertEqual(result["missing_als_items"], [])
        self.assertEqual(result["coverage"]["coverage_fraction"], 1.0)

    def test_review_llp_over_max_flagged_under_max_not(self):
        # Identity from the spec: an LLP item with interval under its ALS
        # max is compliant and one over is not.
        over = [("APU shaft LLP", "LLP", 21000),
                ("fuel-tank flammability check", "FF", 9000),
                ("wing spar DT inspection", "DT", 3000)]
        self.assertEqual(logic.ica_cmr_ali_review(over)["non_compliant"],
                         ["APU shaft LLP"])
        under = [("APU shaft LLP", "LLP", 19000),
                 ("fuel-tank flammability check", "FF", 9000),
                 ("wing spar DT inspection", "DT", 3000)]
        self.assertEqual(logic.ica_cmr_ali_review(under)["non_compliant"], [])

    def test_review_routine_driver_on_canonical_name_still_matches_coverage(
            self):
        # ALS coverage counts canonical presence; a routine-driver item
        # on a canonical name is present but is not compliance-flagged.
        items = [("APU shaft LLP", "ROUTINE", 300),
                 ("wing spar DT inspection", "DT", 3000),
                 ("fuel-tank flammability check", "FF", 9000)]
        result = logic.ica_cmr_ali_review(items)
        self.assertEqual(result["coverage"]["coverage_fraction"], 1.0)
        self.assertEqual(result["non_compliant"], [])

    def test_review_dict_keys_exact(self):
        self.assertEqual(list(logic.ica_cmr_ali_review(WORKED_EXAMPLE).keys()),
                         ["per_item", "class_counts", "coverage",
                          "non_compliant", "missing_als_items"])

    def test_review_empty_items_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.ica_cmr_ali_review([])

    def test_review_deterministic_across_runs(self):
        first = logic.ica_cmr_ali_review(WORKED_EXAMPLE)
        second = logic.ica_cmr_ali_review(WORKED_EXAMPLE)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
