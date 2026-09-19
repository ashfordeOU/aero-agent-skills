"""Contract test for the contamination level calculation leaf (stdlib unittest)."""

import unittest

from q7005_contamination_level_calculation_logic import (
    BAND_AREA,
    PEAK_HEIGHT,
    assess_contamination_level,
    categorize_level,
    deposit_mass_ug,
    net_band_signal,
    species_areal_mass,
    total_contamination_level,
    validate_level_bands,
    validate_sampling_chain,
    validate_species,
)

BANDS = [("level-a", 1.0), ("level-b", 10.0), ("level-c", 25.0)]


def sampling(**kw):
    record = {
        "sampled_area_cm2": 100.0,
        "dilution_factor": 25.0,
        "recovery_fraction": 0.8,
    }
    record.update(kw)
    return record


def species(name="silicone-fluid", **kw):
    record = {
        "name": name,
        "measure_kind": PEAK_HEIGHT,
        "calibration_measure_kind": PEAK_HEIGHT,
        "net_signal": 0.32,
        "calibration_slope": 0.01,
        "calibration_intercept": 0.0,
        "quantification_limit_signal": 0.02,
        "top_standard_signal": 1.0,
    }
    record.update(kw)
    return record


def spec(**kw):
    base = {
        "species": [
            species(),
            species("hydrocarbon-oil", calibration_slope=0.02),
        ],
        "sampling": sampling(),
        "level_bands": BANDS,
    }
    base.update(kw)
    return base


class TestValidateSamplingChain(unittest.TestCase):
    def test_valid_chain_normalises(self):
        norm = validate_sampling_chain(sampling(sampled_area_cm2=100))
        self.assertAlmostEqual(norm["sampled_area_cm2"], 100.0, places=9)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_sampling_chain("area=100")

    def test_missing_key_raises(self):
        record = sampling()
        del record["recovery_fraction"]
        with self.assertRaises(ValueError):
            validate_sampling_chain(record)

    def test_dilution_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_sampling_chain(sampling(dilution_factor=0.5))

    def test_dilution_of_exactly_unity_is_accepted(self):
        norm = validate_sampling_chain(sampling(dilution_factor=1.0))
        self.assertAlmostEqual(norm["dilution_factor"], 1.0, places=9)

    def test_recovery_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_sampling_chain(sampling(recovery_fraction=1.3))

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            validate_sampling_chain(sampling(sampled_area_cm2=0.0))


class TestNetBandSignal(unittest.TestCase):
    def test_baseline_and_blank_are_removed(self):
        self.assertAlmostEqual(net_band_signal(0.40, 0.05, 0.03), 0.32, places=9)

    def test_blank_defaults_to_zero(self):
        self.assertAlmostEqual(net_band_signal(0.40, 0.08), 0.32, places=9)

    def test_signal_below_its_baseline_raises(self):
        with self.assertRaises(ValueError):
            net_band_signal(0.05, 0.40)

    def test_blank_larger_than_the_band_floors_at_zero(self):
        self.assertAlmostEqual(net_band_signal(0.10, 0.05, 0.40), 0.0, places=9)

    def test_negative_blank_raises(self):
        with self.assertRaises(ValueError):
            net_band_signal(0.40, 0.05, -0.01)


class TestValidateSpecies(unittest.TestCase):
    def test_valid_species_normalises(self):
        norm = validate_species(species())
        self.assertEqual(norm["name"], "silicone-fluid")
        self.assertAlmostEqual(norm["calibration_slope"], 0.01, places=9)

    def test_measure_mismatch_raises(self):
        with self.assertRaises(ValueError):
            validate_species(species(measure_kind=BAND_AREA,
                                     calibration_measure_kind=PEAK_HEIGHT))

    def test_matching_band_area_measure_is_accepted(self):
        norm = validate_species(species(measure_kind=BAND_AREA,
                                        calibration_measure_kind=BAND_AREA))
        self.assertEqual(norm["measure_kind"], BAND_AREA)

    def test_unknown_measure_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_species(species(measure_kind="second-derivative",
                                     calibration_measure_kind="second-derivative"))

    def test_blank_name_raises(self):
        with self.assertRaises(ValueError):
            validate_species(species(name="  "))

    def test_zero_slope_raises(self):
        with self.assertRaises(ValueError):
            validate_species(species(calibration_slope=0.0))

    def test_missing_key_raises(self):
        record = species()
        del record["top_standard_signal"]
        with self.assertRaises(ValueError):
            validate_species(record)


class TestSpeciesArealMass(unittest.TestCase):
    def test_signal_inverts_and_carries_the_sampling_chain(self):
        record = species_areal_mass(species(), sampling())
        self.assertAlmostEqual(record["areal_mass_ug_per_cm2"], 10.0, places=9)
        self.assertFalse(record["sub_limit"])
        self.assertFalse(record["above_top_standard"])

    def test_a_steeper_calibration_gives_less_mass(self):
        record = species_areal_mass(species(calibration_slope=0.02), sampling())
        self.assertAlmostEqual(record["areal_mass_ug_per_cm2"], 5.0, places=9)

    def test_deposit_mass_is_the_uncarried_figure(self):
        self.assertAlmostEqual(deposit_mass_ug(species()), 32.0, places=9)

    def test_intercept_is_subtracted_before_dividing(self):
        self.assertAlmostEqual(
            deposit_mass_ug(species(calibration_intercept=0.02)), 30.0, places=9
        )

    def test_signal_under_the_intercept_floors_at_zero_mass(self):
        self.assertAlmostEqual(
            deposit_mass_ug(species(net_signal=0.01,
                                    calibration_intercept=0.05)),
            0.0,
            places=9,
        )

    def test_signal_exactly_at_the_quantification_limit_is_sub_limit(self):
        record = species_areal_mass(species(net_signal=0.02), sampling())
        self.assertTrue(record["sub_limit"])
        self.assertAlmostEqual(record["lower_bound_ug_per_cm2"], 0.0, places=9)
        self.assertAlmostEqual(
            record["upper_bound_ug_per_cm2"],
            record["quantification_limit_ug_per_cm2"],
            places=9,
        )

    def test_signal_above_the_top_standard_is_marked(self):
        record = species_areal_mass(species(net_signal=1.5), sampling())
        self.assertTrue(record["above_top_standard"])

    def test_signal_exactly_at_the_top_standard_is_not_marked(self):
        record = species_areal_mass(species(net_signal=1.0), sampling())
        self.assertFalse(record["above_top_standard"])


class TestTotalContaminationLevel(unittest.TestCase):
    def test_masses_sum_not_signals(self):
        totals = total_contamination_level(
            [species(), species("hydrocarbon-oil", calibration_slope=0.02)],
            sampling(),
        )
        self.assertAlmostEqual(totals["lower_bound_ug_per_cm2"], 15.0, places=9)
        self.assertAlmostEqual(totals["upper_bound_ug_per_cm2"], 15.0, places=9)
        self.assertFalse(totals["bounded"])

    def test_sub_limit_species_widens_the_interval(self):
        totals = total_contamination_level(
            [species(net_signal=0.288),
             species("trace-plasticiser", net_signal=0.01,
                     quantification_limit_signal=0.064)],
            sampling(),
        )
        self.assertAlmostEqual(totals["lower_bound_ug_per_cm2"], 9.0, places=9)
        self.assertAlmostEqual(totals["upper_bound_ug_per_cm2"], 11.0, places=9)
        self.assertTrue(totals["bounded"])

    def test_empty_species_list_raises(self):
        with self.assertRaises(ValueError):
            total_contamination_level([], sampling())

    def test_duplicate_species_name_raises(self):
        with self.assertRaises(ValueError):
            total_contamination_level([species(), species()], sampling())


class TestLevelBands(unittest.TestCase):
    def test_bands_are_sorted_tightest_first(self):
        ordered = validate_level_bands([("level-c", 25.0), ("level-a", 1.0),
                                        ("level-b", 10.0)])
        self.assertEqual([name for name, _ in ordered],
                         ["level-a", "level-b", "level-c"])

    def test_duplicate_band_name_raises(self):
        with self.assertRaises(ValueError):
            validate_level_bands([("level-a", 1.0), ("level-a", 10.0)])

    def test_malformed_band_raises(self):
        with self.assertRaises(ValueError):
            validate_level_bands([("level-a",), ("level-b", 10.0)])

    def test_non_positive_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_level_bands([("level-a", 0.0), ("level-b", 10.0)])

    def test_value_falls_into_the_tightest_satisfied_band(self):
        self.assertEqual(categorize_level(5.0, BANDS), "level-b")

    def test_value_exactly_on_a_bound_takes_that_band(self):
        self.assertEqual(categorize_level(10.0, BANDS), "level-b")

    def test_value_above_every_band_has_no_level(self):
        self.assertIsNone(categorize_level(40.0, BANDS))

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            categorize_level(-1.0, BANDS)


class TestAssessContaminationLevel(unittest.TestCase):
    def test_nominal_two_species_case_is_unambiguous(self):
        out = assess_contamination_level(spec())
        self.assertAlmostEqual(out["lower_bound_ug_per_cm2"], 15.0, places=9)
        self.assertAlmostEqual(out["upper_bound_ug_per_cm2"], 15.0, places=9)
        self.assertEqual(out["level"], "level-c")
        self.assertTrue(out["unambiguous"])
        self.assertEqual(out["findings"], [])

    def test_sub_limit_species_is_a_finding(self):
        out = assess_contamination_level(
            spec(species=[species(net_signal=0.02)])
        )
        self.assertTrue(any("quantification limit" in f for f in out["findings"]))

    def test_straddled_level_boundary_is_a_finding(self):
        out = assess_contamination_level(
            spec(species=[species(net_signal=0.288),
                          species("trace-plasticiser", net_signal=0.01,
                                  quantification_limit_signal=0.064)])
        )
        self.assertEqual(out["lower_bound_level"], "level-b")
        self.assertEqual(out["upper_bound_level"], "level-c")
        self.assertIsNone(out["level"])
        self.assertTrue(any("straddles" in f for f in out["findings"]))

    def test_total_above_every_band_is_out_of_scale(self):
        out = assess_contamination_level(
            spec(species=[species(net_signal=0.96)])
        )
        self.assertIsNone(out["upper_bound_level"])
        self.assertTrue(any("out of scale" in f for f in out["findings"]))

    def test_species_above_its_top_standard_is_a_finding(self):
        out = assess_contamination_level(
            spec(species=[species(net_signal=1.5, top_standard_signal=1.0)],
                 level_bands=[("level-c", 25.0), ("level-d", 100.0)])
        )
        self.assertTrue(any("top calibration standard" in f
                            for f in out["findings"]))

    def test_measure_mismatch_raises_in_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_contamination_level(
                spec(species=[species(measure_kind=BAND_AREA)])
            )

    def test_missing_key_raises(self):
        broken = spec()
        del broken["level_bands"]
        with self.assertRaises(ValueError):
            assess_contamination_level(broken)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_contamination_level(["species"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
