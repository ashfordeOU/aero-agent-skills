"""Contract test for the indirect extract IR analysis leaf (stdlib unittest)."""

import unittest

from q7005_ir_analysis_of_extract_logic import (
    AMBIGUITY_MARGIN,
    BLANK_SHARE_LIMIT,
    QUANTIFICATION_FLOOR_ABS,
    areal_mass_ug_per_cm2,
    assess_extract_analysis,
    blank_share,
    cast_film_mass_ug,
    dilution_factor,
    extract_mass_ug,
    match_reference_spectra,
    net_absorbance,
    score_reference,
    surface_mass_ug,
    validate_extraction_record,
)

SILICONE = [800.0, 1020.0, 1090.0, 1260.0]
HYDROCARBON = [1378.0, 1460.0, 2855.0, 2925.0]
PLASTICISER = [1075.0, 1125.0, 1280.0, 1725.0]
LIBRARY = {
    "silicone-fluid": SILICONE,
    "hydrocarbon-oil": HYDROCARBON,
    "phthalate-plasticiser": PLASTICISER,
}


def sampling(**kw):
    record = {
        "sampled_area_cm2": 100.0,
        "extract_volume_ml": 50.0,
        "cast_aliquot_ml": 2.0,
        "recovery_fraction": 0.8,
    }
    record.update(kw)
    return record


def spec(**kw):
    base = {
        "sampling": sampling(),
        "gross_absorbance": 0.520,
        "baseline_absorbance": 0.020,
        "blank_absorbance": 0.010,
        "response_abs_per_ug": 0.010,
    }
    base.update(kw)
    return base


class TestValidateExtractionRecord(unittest.TestCase):
    def test_valid_record_is_normalised_to_floats(self):
        norm = validate_extraction_record(sampling(sampled_area_cm2=100))
        self.assertIsInstance(norm["sampled_area_cm2"], float)
        self.assertAlmostEqual(norm["recovery_fraction"], 0.8, places=9)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_extraction_record(["area", 100.0])

    def test_missing_key_raises(self):
        record = sampling()
        del record["recovery_fraction"]
        with self.assertRaises(ValueError):
            validate_extraction_record(record)

    def test_zero_sampled_area_raises(self):
        with self.assertRaises(ValueError):
            validate_extraction_record(sampling(sampled_area_cm2=0.0))

    def test_boolean_area_is_rejected_not_coerced(self):
        with self.assertRaises(ValueError):
            validate_extraction_record(sampling(sampled_area_cm2=True))

    def test_aliquot_larger_than_extract_raises(self):
        with self.assertRaises(ValueError):
            validate_extraction_record(
                sampling(extract_volume_ml=5.0, cast_aliquot_ml=10.0)
            )

    def test_recovery_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_extraction_record(sampling(recovery_fraction=1.2))

    def test_recovery_of_exactly_unity_is_accepted(self):
        norm = validate_extraction_record(sampling(recovery_fraction=1.0))
        self.assertAlmostEqual(norm["recovery_fraction"], 1.0, places=9)

    def test_non_finite_volume_raises(self):
        with self.assertRaises(ValueError):
            validate_extraction_record(sampling(extract_volume_ml=float("inf")))


class TestNetAbsorbance(unittest.TestCase):
    def test_blank_is_subtracted(self):
        self.assertAlmostEqual(net_absorbance(0.52, 0.02, 0.01), 0.49, places=9)

    def test_absent_blank_defaults_to_zero(self):
        self.assertAlmostEqual(net_absorbance(0.52, 0.02), 0.50, places=9)

    def test_band_below_its_baseline_raises(self):
        with self.assertRaises(ValueError):
            net_absorbance(0.02, 0.52, 0.0)

    def test_blank_exceeding_the_band_raises(self):
        with self.assertRaises(ValueError):
            net_absorbance(0.10, 0.02, 0.50)

    def test_negative_blank_raises(self):
        with self.assertRaises(ValueError):
            net_absorbance(0.52, 0.02, -0.01)

    def test_noise_level_negative_net_is_floored_at_zero(self):
        self.assertAlmostEqual(net_absorbance(0.100000, 0.100050, 0.0), 0.0, places=9)


class TestBlankShare(unittest.TestCase):
    def test_share_is_the_blank_over_the_band(self):
        self.assertAlmostEqual(blank_share(1.02, 0.02, 0.10), 0.10, places=9)

    def test_zero_band_above_baseline_raises(self):
        with self.assertRaises(ValueError):
            blank_share(0.02, 0.02, 0.0)


class TestMassChain(unittest.TestCase):
    def test_cast_film_mass_divides_by_the_response(self):
        self.assertAlmostEqual(cast_film_mass_ug(0.49, 0.010), 49.0, places=9)

    def test_zero_net_gives_zero_cast_mass(self):
        self.assertAlmostEqual(cast_film_mass_ug(0.0, 0.010), 0.0, places=9)

    def test_zero_response_raises(self):
        with self.assertRaises(ValueError):
            cast_film_mass_ug(0.49, 0.0)

    def test_dilution_factor_restores_the_whole_extract(self):
        self.assertAlmostEqual(dilution_factor(50.0, 2.0), 25.0, places=9)

    def test_extract_mass_applies_the_dilution(self):
        self.assertAlmostEqual(extract_mass_ug(49.0, 50.0, 2.0), 1225.0, places=9)

    def test_surface_mass_divides_by_recovery(self):
        self.assertAlmostEqual(surface_mass_ug(1225.0, 0.8), 1531.25, places=9)

    def test_recovery_above_unity_raises_in_surface_mass(self):
        with self.assertRaises(ValueError):
            surface_mass_ug(1225.0, 1.5)

    def test_areal_mass_divides_by_the_sampled_area(self):
        self.assertAlmostEqual(
            areal_mass_ug_per_cm2(1531.25, 100.0), 15.3125, places=9
        )

    def test_zero_area_raises_in_areal_mass(self):
        with self.assertRaises(ValueError):
            areal_mass_ug_per_cm2(1531.25, 0.0)


class TestScoreReference(unittest.TestCase):
    def test_full_coverage_scores_unity(self):
        record = score_reference(list(SILICONE), SILICONE)
        self.assertAlmostEqual(record["coverage"], 1.0, places=9)
        self.assertEqual(record["missing_bands"], [])

    def test_band_inside_tolerance_still_matches(self):
        record = score_reference([803.0, 1024.0, 1086.0, 1256.0], SILICONE)
        self.assertAlmostEqual(record["coverage"], 1.0, places=9)

    def test_band_outside_tolerance_is_missing(self):
        record = score_reference([800.0, 1020.0, 1090.0, 1400.0], SILICONE)
        self.assertAlmostEqual(record["coverage"], 0.75, places=9)
        self.assertEqual(record["missing_bands"], [1260.0])

    def test_unexplained_observed_bands_are_reported(self):
        record = score_reference(list(SILICONE) + [1725.0], SILICONE)
        self.assertEqual(record["unexplained_observed"], [1725.0])

    def test_single_matched_band_is_flagged(self):
        record = score_reference([1020.0], SILICONE)
        self.assertTrue(record["single_band_support"])

    def test_empty_observed_bands_raise(self):
        with self.assertRaises(ValueError):
            score_reference([], SILICONE)

    def test_negative_wavenumber_raises(self):
        with self.assertRaises(ValueError):
            score_reference([-800.0], SILICONE)

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            score_reference(list(SILICONE), SILICONE, tolerance_cm1=0.0)


class TestMatchReferenceSpectra(unittest.TestCase):
    def test_clear_winner_is_identified(self):
        out = match_reference_spectra(list(HYDROCARBON), LIBRARY)
        self.assertEqual(out["best"], "hydrocarbon-oil")
        self.assertFalse(out["ambiguous"])
        self.assertEqual(out["identification"], "hydrocarbon-oil")

    def test_two_fully_covered_references_are_ambiguous(self):
        out = match_reference_spectra(SILICONE + PLASTICISER, LIBRARY)
        self.assertTrue(out["ambiguous"])
        self.assertIsNone(out["identification"])
        self.assertIn("silicone-fluid", out["contenders"])
        self.assertIn("phthalate-plasticiser", out["contenders"])

    def test_ranking_is_ordered_by_coverage(self):
        out = match_reference_spectra(list(SILICONE), LIBRARY)
        coverages = [r["coverage"] for r in out["ranking"]]
        self.assertEqual(coverages, sorted(coverages, reverse=True))

    def test_empty_library_raises(self):
        with self.assertRaises(ValueError):
            match_reference_spectra(list(SILICONE), {})

    def test_margin_must_be_positive(self):
        with self.assertRaises(ValueError):
            match_reference_spectra(list(SILICONE), LIBRARY, ambiguity_margin=0.0)

    def test_gap_exactly_at_the_margin_counts_as_ambiguous(self):
        library = {
            "ten-band-a": [float(1000 + 10 * i) for i in range(10)],
            "ten-band-b": [float(1000 + 10 * i) for i in range(9)] + [3500.0],
        }
        observed = [float(1000 + 10 * i) for i in range(10)]
        out = match_reference_spectra(observed, library,
                                      ambiguity_margin=AMBIGUITY_MARGIN)
        self.assertTrue(out["ambiguous"])


class TestAssessExtractAnalysis(unittest.TestCase):
    def test_nominal_case_reduces_to_an_areal_mass(self):
        out = assess_extract_analysis(spec())
        self.assertAlmostEqual(out["net_absorbance"], 0.49, places=9)
        self.assertAlmostEqual(out["cast_film_mass_ug"], 49.0, places=9)
        self.assertAlmostEqual(out["extract_mass_ug"], 1225.0, places=9)
        self.assertAlmostEqual(out["surface_mass_ug"], 1531.25, places=9)
        self.assertAlmostEqual(out["areal_mass_ug_per_cm2"], 15.3125, places=9)
        self.assertTrue(out["quantifiable"])

    def test_blank_share_at_the_limit_raises_no_finding(self):
        out = assess_extract_analysis(
            spec(gross_absorbance=1.02, baseline_absorbance=0.02,
                 blank_absorbance=0.10)
        )
        self.assertAlmostEqual(out["blank_share"], BLANK_SHARE_LIMIT, places=9)
        self.assertEqual(out["findings"], [])

    def test_blank_dominated_band_is_a_finding(self):
        out = assess_extract_analysis(
            spec(gross_absorbance=1.02, baseline_absorbance=0.02,
                 blank_absorbance=0.50)
        )
        self.assertTrue(any("solvent blank" in f for f in out["findings"]))
        self.assertFalse(out["acceptable"])

    def test_net_at_the_quantification_floor_is_bounded_not_quantified(self):
        out = assess_extract_analysis(
            spec(gross_absorbance=QUANTIFICATION_FLOOR_ABS,
                 baseline_absorbance=0.0, blank_absorbance=0.0)
        )
        self.assertFalse(out["quantifiable"])
        self.assertTrue(out["bounded_upper_limit"])

    def test_missing_required_key_raises(self):
        broken = spec()
        del broken["response_abs_per_ug"]
        with self.assertRaises(ValueError):
            assess_extract_analysis(broken)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_extract_analysis("extract")

    def test_identification_is_carried_when_a_library_is_supplied(self):
        out = assess_extract_analysis(
            spec(observed_bands=list(HYDROCARBON), reference_library=LIBRARY)
        )
        self.assertEqual(out["identification"]["identification"], "hydrocarbon-oil")

    def test_ambiguous_identification_is_a_finding(self):
        out = assess_extract_analysis(
            spec(observed_bands=SILICONE + PLASTICISER, reference_library=LIBRARY)
        )
        self.assertTrue(any("ambiguous" in f for f in out["findings"]))

    def test_single_band_identification_is_a_finding(self):
        out = assess_extract_analysis(
            spec(observed_bands=[1020.0], reference_library=LIBRARY)
        )
        self.assertTrue(any("one band only" in f for f in out["findings"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
