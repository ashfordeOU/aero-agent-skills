"""Contract tests for the ECSS-Q-ST-70-29 offgassing test-report logic."""

import unittest

from q7029_test_report_logic import (
    CONCLUSION_ACCEPTED,
    CONCLUSION_OPEN,
    CONCLUSION_REJECTED,
    REQUIRED_SECTIONS,
    build_report,
    cross_check_tables,
    derive_conclusion,
    recompute_governing_t_value,
    recompute_total_mass_ug,
    totals_agree,
    validate_identification,
    validate_table,
)

IDENT = {
    "article": "cable tie, polyamide",
    "batch": "LOT-4471",
    "tested_mass_g": 50.0,
    "vessel_volume_m3": 0.002,
    "conditioning_temperature_c": 50.0,
    "conditioning_duration_h": 72.0,
    "analytical_method": "thermal desorption with mass-spectrometric detection",
}

PRODUCTS = [
    {"compound": "toluene", "grade": "confirmed"},
    {"compound": "hexanal", "grade": "confirmed"},
]

CONCENTRATIONS = [
    {"compound": "toluene", "reported_mass_ug": 10.0},
    {"compound": "hexanal", "reported_mass_ug": 25.0},
]

ASSESSMENTS = [
    {"compound": "toluene", "verdict": "met", "group": "irritant", "t_ratio": 0.2},
    {"compound": "hexanal", "verdict": "met", "group": "irritant", "t_ratio": 0.3},
]


class IdentificationTests(unittest.TestCase):
    def test_complete_block_is_normalised(self):
        block = validate_identification(IDENT)
        self.assertEqual(block["batch"], "LOT-4471")
        self.assertAlmostEqual(block["tested_mass_g"], 50.0, places=9)

    def test_missing_field_rejected(self):
        bad = dict(IDENT)
        del bad["analytical_method"]
        with self.assertRaises(ValueError):
            validate_identification(bad)

    def test_empty_article_rejected(self):
        with self.assertRaises(ValueError):
            validate_identification(dict(IDENT, article="   "))

    def test_zero_tested_mass_rejected(self):
        with self.assertRaises(ValueError):
            validate_identification(dict(IDENT, tested_mass_g=0.0))

    def test_negative_conditioning_temperature_allowed(self):
        block = validate_identification(dict(IDENT, conditioning_temperature_c=-20.0))
        self.assertAlmostEqual(block["conditioning_temperature_c"], -20.0, places=9)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_identification(dict(IDENT, conditioning_temperature_c=-300.0))

    def test_non_mapping_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_identification(["article"])


class TableTests(unittest.TestCase):
    def test_valid_table_is_returned(self):
        rows = validate_table(PRODUCTS, "products", ("compound", "grade"))
        self.assertEqual(len(rows), 2)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_table([], "products", ("compound", "grade"))

    def test_duplicate_compound_row_rejected(self):
        rows = PRODUCTS + [{"compound": "toluene", "grade": "tentative"}]
        with self.assertRaises(ValueError):
            validate_table(rows, "products", ("compound", "grade"))

    def test_row_missing_a_required_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_table([{"compound": "toluene"}], "products", ("compound", "grade"))


class CrossCheckTests(unittest.TestCase):
    def test_matching_tables_report_nothing(self):
        cross = cross_check_tables(PRODUCTS, CONCENTRATIONS, ASSESSMENTS)
        for key in cross:
            self.assertEqual(cross[key], [])

    def test_identified_compound_without_a_concentration_is_caught(self):
        cross = cross_check_tables(PRODUCTS, CONCENTRATIONS[:1], ASSESSMENTS)
        self.assertEqual(cross["identified_without_concentration"], ["hexanal"])

    def test_measured_compound_never_identified_is_caught(self):
        extra = CONCENTRATIONS + [{"compound": "benzene", "reported_mass_ug": 1.0}]
        cross = cross_check_tables(PRODUCTS, extra, ASSESSMENTS)
        self.assertEqual(cross["measured_without_identification"], ["benzene"])

    def test_assessed_compound_never_quantified_is_caught(self):
        extra = ASSESSMENTS + [
            {"compound": "benzene", "verdict": "met", "group": "irritant", "t_ratio": 0.1}
        ]
        cross = cross_check_tables(PRODUCTS, CONCENTRATIONS, extra)
        self.assertEqual(cross["assessed_without_concentration"], ["benzene"])


class RecomputationTests(unittest.TestCase):
    def test_total_mass_is_the_sum_of_the_rows(self):
        self.assertAlmostEqual(recompute_total_mass_ug(CONCENTRATIONS), 35.0, places=9)

    def test_negative_reported_mass_rejected(self):
        with self.assertRaises(ValueError):
            recompute_total_mass_ug([{"compound": "toluene", "reported_mass_ug": -1.0}])

    def test_empty_concentration_table_rejected(self):
        with self.assertRaises(ValueError):
            recompute_total_mass_ug([])

    def test_governing_total_adds_within_a_group(self):
        self.assertAlmostEqual(recompute_governing_t_value(ASSESSMENTS), 0.5, places=9)

    def test_governing_total_takes_the_largest_group(self):
        rows = ASSESSMENTS + [
            {"compound": "benzene", "verdict": "met", "group": "haematotoxic", "t_ratio": 0.8}
        ]
        self.assertAlmostEqual(recompute_governing_t_value(rows), 0.8, places=9)

    def test_rows_without_a_ratio_contribute_nothing(self):
        rows = [{"compound": "toluene", "verdict": "open", "t_ratio": None}]
        self.assertAlmostEqual(recompute_governing_t_value(rows), 0.0, places=9)

    def test_totals_agree_on_an_exact_match(self):
        self.assertTrue(totals_agree(35.0, recompute_total_mass_ug(CONCENTRATIONS)))

    def test_totals_disagree_when_a_row_is_missing(self):
        self.assertFalse(totals_agree(35.0, recompute_total_mass_ug(CONCENTRATIONS[:1])))


class ConclusionTests(unittest.TestCase):
    def test_all_met_and_no_open_item_is_accepted(self):
        self.assertEqual(derive_conclusion(ASSESSMENTS, []), CONCLUSION_ACCEPTED)

    def test_a_breached_row_rejects(self):
        rows = [dict(ASSESSMENTS[0], verdict="breached"), ASSESSMENTS[1]]
        self.assertEqual(derive_conclusion(rows, []), CONCLUSION_REJECTED)

    def test_an_open_item_leaves_the_report_open(self):
        self.assertEqual(derive_conclusion(ASSESSMENTS, ["no limit for x"]), CONCLUSION_OPEN)

    def test_an_open_row_leaves_the_report_open(self):
        rows = [dict(ASSESSMENTS[0], verdict="open"), ASSESSMENTS[1]]
        self.assertEqual(derive_conclusion(rows, []), CONCLUSION_OPEN)

    def test_unknown_verdict_rejected(self):
        rows = [dict(ASSESSMENTS[0], verdict="probably fine")]
        with self.assertRaises(ValueError):
            derive_conclusion(rows, [])


class BuildReportTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "identification": IDENT,
            "products": PRODUCTS,
            "concentrations": CONCENTRATIONS,
            "assessments": ASSESSMENTS,
            "stated_conclusion": CONCLUSION_ACCEPTED,
            "stated_total_mass_ug": 35.0,
            "stated_governing_t_value": 0.5,
        }
        spec.update(overrides)
        return spec

    def test_consistent_report_is_issuable(self):
        report = build_report(self._spec())
        self.assertTrue(report["issuable"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["sections"], list(REQUIRED_SECTIONS))

    def test_recomputed_totals_are_reported(self):
        report = build_report(self._spec())
        self.assertAlmostEqual(report["recomputed_total_mass_ug"], 35.0, places=9)
        self.assertAlmostEqual(report["recomputed_governing_t_value"], 0.5, places=9)

    def test_overstated_total_is_caught(self):
        report = build_report(self._spec(stated_total_mass_ug=50.0))
        self.assertFalse(report["issuable"])
        self.assertFalse(report["totals_consistent"])

    def test_overstated_toxicity_total_is_caught(self):
        report = build_report(self._spec(stated_governing_t_value=0.2))
        self.assertFalse(report["totals_consistent"])

    def test_conclusion_contradicting_the_tables_is_caught(self):
        rows = [dict(ASSESSMENTS[0], verdict="breached"), ASSESSMENTS[1]]
        report = build_report(self._spec(assessments=rows, stated_governing_t_value=0.5))
        self.assertEqual(report["derived_conclusion"], CONCLUSION_REJECTED)
        self.assertFalse(report["issuable"])

    def test_orphan_row_makes_the_report_unissuable(self):
        report = build_report(self._spec(concentrations=CONCENTRATIONS[:1],
                                         stated_total_mass_ug=10.0))
        self.assertFalse(report["issuable"])
        self.assertTrue(
            any("identified without concentration" in f for f in report["findings"])
        )

    def test_open_items_stay_visible_in_the_issued_report(self):
        report = build_report(self._spec(open_items=["no limit for hexanal"],
                                         stated_conclusion=CONCLUSION_OPEN))
        self.assertEqual(report["derived_conclusion"], CONCLUSION_OPEN)
        self.assertEqual(report["open_items"], ["no limit for hexanal"])

    def test_unknown_stated_conclusion_rejected(self):
        with self.assertRaises(ValueError):
            build_report(self._spec(stated_conclusion="probably fine"))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["concentrations"]
        with self.assertRaises(ValueError):
            build_report(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            build_report(["identification"])


if __name__ == "__main__":
    unittest.main()
