"""Contract test for the q40-02-step2-identify-assess leaf (stdlib unittest)."""

import unittest

from q40_02_step2_identify_assess_logic import (
    IDENTIFICATION_SOURCES,
    LIKELIHOOD_BANDS,
    SEVERITY_CATEGORIES,
    assess_hazard,
    assess_identification_and_assessment,
    likelihood_band,
    risk_acceptability,
    risk_index,
    source_coverage,
    validate_hazard,
)


def hazard(hid="HZ-1", **kw):
    record = {
        "id": hid,
        "source": "generic-hazard-library",
        "severity": "critical",
        "likelihood": "remote",
        "severity_evidence": True,
        "likelihood_evidence": True,
    }
    record.update(kw)
    return record


def full_list():
    return [
        hazard("HZ-1", source="generic-hazard-library"),
        hazard("HZ-2", source="system-functions", severity="major"),
        hazard("HZ-3", source="planned-operations", severity="minor"),
        hazard(
            "HZ-4",
            source="induced-and-natural-environments",
            severity="catastrophic",
            likelihood="improbable",
        ),
    ]


class TestLikelihoodBand(unittest.TestCase):
    def test_high_probability_is_probable(self):
        self.assertEqual(likelihood_band(0.4), "probable")

    def test_upper_bound_of_a_band_is_inclusive(self):
        self.assertEqual(likelihood_band(1.0e-2), "probable")
        self.assertEqual(likelihood_band(1.0e-3), "occasional")
        self.assertEqual(likelihood_band(1.0e-5), "remote")

    def test_just_under_a_bound_drops_a_band(self):
        self.assertEqual(likelihood_band(9.0e-3), "occasional")
        self.assertEqual(likelihood_band(9.0e-6), "improbable")

    def test_zero_probability_is_improbable(self):
        self.assertEqual(likelihood_band(0.0), "improbable")

    def test_probability_above_one_raises(self):
        with self.assertRaises(ValueError):
            likelihood_band(1.5)

    def test_negative_probability_raises(self):
        with self.assertRaises(ValueError):
            likelihood_band(-1.0e-3)

    def test_non_numeric_probability_raises(self):
        with self.assertRaises(ValueError):
            likelihood_band("remote")

    def test_boolean_probability_raises(self):
        with self.assertRaises(ValueError):
            likelihood_band(True)


class TestRiskIndex(unittest.TestCase):
    def test_worst_pair_is_index_one(self):
        self.assertEqual(risk_index("catastrophic", "probable"), 1)

    def test_mildest_pair_is_index_sixteen(self):
        self.assertEqual(risk_index("minor", "improbable"), 16)

    def test_index_worsens_as_severity_worsens(self):
        self.assertLess(
            risk_index("catastrophic", "remote"), risk_index("minor", "remote")
        )

    def test_index_worsens_as_likelihood_rises(self):
        self.assertLess(
            risk_index("critical", "probable"), risk_index("critical", "improbable")
        )

    def test_every_matrix_cell_is_unique(self):
        values = [
            risk_index(s, l) for s in SEVERITY_CATEGORIES for l in LIKELIHOOD_BANDS
        ]
        self.assertEqual(sorted(values), list(range(1, 17)))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            risk_index("annoying", "remote")

    def test_unknown_likelihood_raises(self):
        with self.assertRaises(ValueError):
            risk_index("critical", "unlikely-ish")


class TestAcceptability(unittest.TestCase):
    def test_worst_cells_are_unacceptable(self):
        self.assertEqual(risk_acceptability(1), "unacceptable")
        self.assertEqual(risk_acceptability(5), "unacceptable")

    def test_next_band_is_undesirable(self):
        self.assertEqual(risk_acceptability(6), "undesirable")
        self.assertEqual(risk_acceptability(9), "undesirable")

    def test_review_band_boundaries(self):
        self.assertEqual(risk_acceptability(10), "acceptable-with-review")
        self.assertEqual(risk_acceptability(14), "acceptable-with-review")

    def test_mildest_band_is_acceptable(self):
        self.assertEqual(risk_acceptability(15), "acceptable")
        self.assertEqual(risk_acceptability(16), "acceptable")

    def test_index_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            risk_acceptability(0)
        with self.assertRaises(ValueError):
            risk_acceptability(17)

    def test_non_integer_index_raises(self):
        with self.assertRaises(ValueError):
            risk_acceptability(4.5)


class TestValidateHazard(unittest.TestCase):
    def test_probability_overrides_a_declared_band(self):
        norm = validate_hazard(hazard(likelihood="probable", probability=1.0e-6))
        self.assertEqual(norm["likelihood"], "improbable")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(["HZ-1"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(""))

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(source="a-hunch"))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(severity="inconvenient"))

    def test_no_likelihood_and_no_probability_raises(self):
        record = hazard()
        del record["likelihood"]
        with self.assertRaises(ValueError):
            validate_hazard(record)

    def test_non_boolean_evidence_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(severity_evidence="yes"))


class TestAssessHazard(unittest.TestCase):
    def test_supported_hazard_has_no_findings(self):
        result = assess_hazard(hazard())
        self.assertTrue(result["supported"])
        self.assertEqual(result["risk_index"], risk_index("critical", "remote"))

    def test_unsupported_severity_is_a_finding(self):
        result = assess_hazard(hazard(severity_evidence=False))
        self.assertIn("severity-not-supported-by-evidence", result["findings"])
        self.assertFalse(result["supported"])

    def test_unsupported_likelihood_is_a_finding(self):
        result = assess_hazard(hazard(likelihood_evidence=False))
        self.assertIn("likelihood-not-supported-by-evidence", result["findings"])

    def test_acceptability_follows_the_index(self):
        result = assess_hazard(hazard(severity="catastrophic", likelihood="probable"))
        self.assertEqual(result["acceptability"], "unacceptable")


class TestSourceCoverage(unittest.TestCase):
    def test_all_four_sources_worked(self):
        coverage = source_coverage(full_list())
        self.assertEqual(coverage["untouched"], [])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=9)

    def test_single_source_list_reports_three_untouched(self):
        coverage = source_coverage([hazard("HZ-1")])
        self.assertEqual(len(coverage["untouched"]), 3)
        self.assertAlmostEqual(coverage["coverage_fraction"], 0.25, places=9)

    def test_untouched_list_keeps_declared_order(self):
        coverage = source_coverage([hazard("HZ-1", source="planned-operations")])
        self.assertEqual(
            coverage["untouched"],
            [s for s in IDENTIFICATION_SOURCES if s != "planned-operations"],
        )

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            source_coverage(hazard())


class TestFullAssessment(unittest.TestCase):
    def test_complete_list_has_no_findings(self):
        result = assess_identification_and_assessment(full_list())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_untouched_source_is_a_finding(self):
        result = assess_identification_and_assessment([hazard("HZ-1")])
        self.assertIn(
            "identification-source-not-worked:system-functions", result["findings"]
        )
        self.assertFalse(result["complete"])

    def test_unacceptable_ids_are_listed(self):
        hazards = full_list()
        hazards.append(
            hazard("HZ-5", severity="catastrophic", likelihood="occasional")
        )
        result = assess_identification_and_assessment(hazards)
        self.assertIn("HZ-5", result["unacceptable_ids"])

    def test_distribution_counts_every_entry(self):
        result = assess_identification_and_assessment(full_list())
        self.assertEqual(sum(result["acceptability_distribution"].values()), 4)

    def test_duplicate_hazard_id_raises(self):
        hazards = full_list()
        hazards.append(hazard("HZ-1", source="system-functions"))
        with self.assertRaises(ValueError):
            assess_identification_and_assessment(hazards)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            assess_identification_and_assessment([])


if __name__ == "__main__":
    unittest.main()
