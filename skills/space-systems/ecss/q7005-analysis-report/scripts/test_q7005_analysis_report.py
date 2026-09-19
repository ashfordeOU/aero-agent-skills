"""Contract test for the IR contamination analysis-report leaf (unittest)."""

import unittest

from q7005_analysis_report_logic import (
    DEFAULT_RESOLUTION_MG_M2,
    JUDGEMENT_ABOVE,
    JUDGEMENT_MEETS,
    JUDGEMENT_NOT_DEMONSTRATED,
    METHOD_INDIRECT,
    NOT_REPORTABLE,
    REPORTABLE,
    REPORTABLE_WITH_OBSERVATIONS,
    SECTION_JUDGEMENT,
    SECTION_ORDER,
    grade_report,
    grade_report_set,
    implied_judgement,
    missing_fields,
    recompute_level,
    required_fields,
    section_fields,
    validate_report,
    values_agree,
)


def report(item="mirror-cell", **kw):
    record = {
        "item": item,
        "method_name": "attenuated-reflection-read",
        "method_kind": "direct",
        "sampled_area_m2": 0.05,
        "sample_spectrum_reference": "SP-1001",
        "background_spectrum_reference": "SP-1000",
        "residue_mass_mg": 0.05,
        "reported_level_mg_m2": 1.0,
        "required_limit_mg_m2": 2.0,
        "judgement": JUDGEMENT_MEETS,
        "expanded_uncertainty_mg_m2": 0.05,
    }
    record.update(kw)
    return record


def indirect_report(**kw):
    record = report(
        method_kind=METHOD_INDIRECT,
        solvent="isopropanol",
        recovery_fraction=0.80,
        blank_spectrum_reference="SP-0999",
        residue_mass_mg=0.04,
        reported_level_mg_m2=1.0,
    )
    record.update(kw)
    return record


class TestSections(unittest.TestCase):
    def test_every_section_declares_fields(self):
        for section in SECTION_ORDER:
            self.assertTrue(section_fields(section))

    def test_the_judgement_section_carries_the_limit(self):
        self.assertIn("required_limit_mg_m2", section_fields(SECTION_JUDGEMENT))

    def test_unknown_section_raises(self):
        with self.assertRaises(ValueError):
            section_fields("conclusions")


class TestRecomputeLevel(unittest.TestCase):
    def test_a_direct_level_is_mass_over_area(self):
        self.assertAlmostEqual(recompute_level(0.05, 0.05), 1.0, places=9)

    def test_a_partial_recovery_raises_the_level(self):
        self.assertAlmostEqual(recompute_level(0.04, 0.05, 0.80), 1.0, places=9)

    def test_a_zero_area_raises(self):
        with self.assertRaises(ValueError):
            recompute_level(0.05, 0.0)

    def test_a_zero_recovery_raises(self):
        with self.assertRaises(ValueError):
            recompute_level(0.05, 0.05, 0.0)

    def test_a_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            recompute_level(-0.01, 0.05)


class TestValuesAgree(unittest.TestCase):
    def test_an_exact_match_agrees(self):
        self.assertTrue(values_agree(1.0, 1.0))

    def test_a_value_half_a_step_away_still_agrees(self):
        self.assertTrue(values_agree(1.0, 1.0 + DEFAULT_RESOLUTION_MG_M2 / 2.0))

    def test_a_value_well_past_the_step_does_not(self):
        self.assertFalse(values_agree(1.0, 1.4))

    def test_a_zero_resolution_raises(self):
        with self.assertRaises(ValueError):
            values_agree(1.0, 1.0, 0.0)


class TestImpliedJudgement(unittest.TestCase):
    def test_a_level_under_the_limit_meets_it(self):
        self.assertEqual(implied_judgement(1.0, 2.0), JUDGEMENT_MEETS)

    def test_a_level_exactly_on_the_limit_meets_it(self):
        self.assertEqual(implied_judgement(2.0, 2.0), JUDGEMENT_MEETS)

    def test_a_level_over_the_limit_is_above_it(self):
        self.assertEqual(implied_judgement(3.0, 2.0), JUDGEMENT_ABOVE)

    def test_a_coarse_non_detect_bound_demonstrates_nothing(self):
        self.assertEqual(
            implied_judgement(4.0, 2.0, detected=False),
            JUDGEMENT_NOT_DEMONSTRATED,
        )

    def test_a_non_boolean_detected_raises(self):
        with self.assertRaises(ValueError):
            implied_judgement(1.0, 2.0, detected="yes")


class TestRequiredFields(unittest.TestCase):
    def test_a_direct_report_does_not_owe_a_solvent(self):
        self.assertNotIn("solvent", required_fields(report()))

    def test_an_indirect_report_owes_solvent_recovery_and_blank(self):
        owed = required_fields(indirect_report())
        for name in ("solvent", "recovery_fraction", "blank_spectrum_reference"):
            self.assertIn(name, owed)

    def test_naming_a_contaminant_adds_the_reference_spectrum(self):
        owed = required_fields(report(identified_species="silicone-oil"))
        self.assertIn("reference_spectrum_reference", owed)

    def test_a_non_detect_owes_the_quantitation_limit_not_a_level(self):
        owed = required_fields(
            report(detected=False, reported_level_mg_m2=None,
                   quantitation_limit_mg_m2=0.3)
        )
        self.assertIn("quantitation_limit_mg_m2", owed)
        self.assertNotIn("reported_level_mg_m2", owed)

    def test_required_fields_have_no_duplicates(self):
        owed = required_fields(indirect_report())
        self.assertEqual(len(owed), len(set(owed)))

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            required_fields("a report")


class TestMissingFields(unittest.TestCase):
    def test_a_full_report_is_missing_nothing(self):
        self.assertEqual(missing_fields(report()), ())

    def test_an_empty_string_counts_as_missing(self):
        self.assertIn(
            "sample_spectrum_reference",
            missing_fields(report(sample_spectrum_reference="   ")),
        )

    def test_an_indirect_report_without_a_blank_is_incomplete(self):
        self.assertIn(
            "blank_spectrum_reference",
            missing_fields(indirect_report(blank_spectrum_reference=None)),
        )


class TestValidateReport(unittest.TestCase):
    def test_a_valid_report_is_normalized(self):
        norm = validate_report(report())
        self.assertEqual(norm["item"], "mirror-cell")

    def test_an_empty_item_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(item=""))

    def test_an_unknown_method_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(method_kind="sniff-test"))

    def test_an_unknown_judgement_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(judgement="looks-clean"))

    def test_a_negative_area_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(sampled_area_m2=-0.05))

    def test_a_recovery_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_report(indirect_report(recovery_fraction=1.6))

    def test_a_detection_carrying_only_a_quantitation_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_report(
                report(reported_level_mg_m2=None, quantitation_limit_mg_m2=0.3)
            )


class TestGradeReport(unittest.TestCase):
    def test_a_complete_consistent_report_is_reportable(self):
        row = grade_report(report())
        self.assertEqual(row["verdict"], REPORTABLE)
        self.assertEqual(row["blocking_findings"], [])
        self.assertAlmostEqual(row["completeness"], 1.0, places=9)

    def test_an_indirect_report_recomputes_through_its_recovery(self):
        row = grade_report(indirect_report())
        self.assertAlmostEqual(row["recomputed_level_mg_m2"], 1.0, places=9)
        self.assertEqual(row["verdict"], REPORTABLE)

    def test_a_level_that_does_not_follow_from_the_inputs_blocks(self):
        row = grade_report(report(reported_level_mg_m2=0.4))
        self.assertEqual(row["verdict"], NOT_REPORTABLE)
        self.assertIn(
            "stated-level-does-not-follow-from-the-reported-inputs",
            row["blocking_findings"],
        )

    def test_forgetting_the_recovery_is_caught_by_the_recomputation(self):
        row = grade_report(
            indirect_report(reported_level_mg_m2=0.8, recovery_fraction=0.80)
        )
        self.assertEqual(row["verdict"], NOT_REPORTABLE)

    def test_a_named_contaminant_without_a_reference_spectrum_blocks(self):
        row = grade_report(report(identified_species="silicone-oil"))
        self.assertEqual(row["verdict"], NOT_REPORTABLE)
        self.assertIn(
            "named-contaminant-without-a-reference-spectrum",
            row["blocking_findings"],
        )

    def test_a_named_contaminant_with_its_reference_spectrum_passes(self):
        row = grade_report(
            report(
                identified_species="silicone-oil",
                reference_spectrum_reference="REF-204",
            )
        )
        self.assertEqual(row["verdict"], REPORTABLE)

    def test_a_judgement_without_a_limit_blocks(self):
        row = grade_report(report(required_limit_mg_m2=None))
        self.assertEqual(row["verdict"], NOT_REPORTABLE)
        self.assertIn(
            "judgement-without-the-level-it-was-made-against",
            row["blocking_findings"],
        )

    def test_a_judgement_contradicting_the_numbers_blocks(self):
        row = grade_report(report(reported_level_mg_m2=1.0,
                                  required_limit_mg_m2=0.5,
                                  residue_mass_mg=0.05,
                                  judgement=JUDGEMENT_MEETS))
        self.assertEqual(row["verdict"], NOT_REPORTABLE)
        self.assertIn(
            "judgement-contradicts-the-reported-numbers",
            row["blocking_findings"],
        )

    def test_a_missing_spectrum_reference_is_counted_and_blocks(self):
        row = grade_report(report(background_spectrum_reference=None))
        self.assertEqual(row["verdict"], NOT_REPORTABLE)
        self.assertLess(row["completeness"], 1.0)

    def test_a_missing_uncertainty_is_an_observation_not_a_block(self):
        row = grade_report(report(expanded_uncertainty_mg_m2=None))
        self.assertEqual(row["verdict"], REPORTABLE_WITH_OBSERVATIONS)
        self.assertIn("no-expanded-uncertainty-reported", row["observations"])

    def test_an_over_fine_resolution_is_an_observation(self):
        row = grade_report(
            report(reporting_resolution_mg_m2=0.0001,
                   expanded_uncertainty_mg_m2=0.2)
        )
        self.assertEqual(row["verdict"], REPORTABLE_WITH_OBSERVATIONS)
        self.assertIn(
            "level-written-finer-than-its-uncertainty-supports",
            row["observations"],
        )

    def test_a_non_detect_report_is_graded_on_its_bound(self):
        row = grade_report(
            report(
                detected=False,
                reported_level_mg_m2=None,
                quantitation_limit_mg_m2=0.3,
                judgement=JUDGEMENT_MEETS,
            )
        )
        self.assertEqual(row["verdict"], REPORTABLE)
        self.assertEqual(row["implied_judgement"], JUDGEMENT_MEETS)


class TestGradeReportSet(unittest.TestCase):
    def test_a_clean_set_is_clear(self):
        summary = grade_report_set([report("a"), report("b")])
        self.assertTrue(summary["clear"])
        self.assertEqual(summary["not_reportable"], [])

    def test_one_defective_report_clouds_the_set(self):
        summary = grade_report_set(
            [report("a"), report("b", required_limit_mg_m2=None)]
        )
        self.assertFalse(summary["clear"])
        self.assertEqual(summary["not_reportable"], ["b"])

    def test_observations_are_grouped_apart(self):
        summary = grade_report_set(
            [report("a"), report("b", expanded_uncertainty_mg_m2=None)]
        )
        self.assertEqual(summary["with_observations"], ["b"])
        self.assertTrue(summary["clear"])

    def test_duplicate_item_raises(self):
        with self.assertRaises(ValueError):
            grade_report_set([report("a"), report("a")])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            grade_report_set([])


if __name__ == "__main__":
    unittest.main()
