"""Contract tests for the clause 6.4.3.6.2 thermo optical measurement logic."""

import unittest

from e2008_sca_thermo_optical_measurement_process_logic import (
    DEFAULT_ABSORPTANCE_REPEATABILITY,
    DEFAULT_REQUIRED_SCANS,
    absorptance_emittance_ratio,
    assess_thermo_optical_measurement,
    evaluate_sample,
    hemispherical_emittance,
    mean_value,
    reading_spread,
    resolve_subgroup,
    solar_absorptance,
    uncovered_wavelengths_um,
    weighted_reflectance,
)

INSTRUMENTS = {
    "reflectometer_range_um": (0.25, 2.5),
    "emissometer_range_um": (2.0, 25.0),
}


def _solar_bands(reflectance=0.10):
    return [
        {"wavelength_um": 0.5, "weight": 2.0, "reflectance": reflectance},
        {"wavelength_um": 1.0, "weight": 1.0, "reflectance": reflectance},
    ]


def _thermal_bands(reflectance=0.15):
    return [
        {"wavelength_um": 5.0, "weight": 1.0, "reflectance": reflectance},
        {"wavelength_um": 10.0, "weight": 1.0, "reflectance": reflectance},
    ]


def _scan(solar=0.10, thermal=0.15):
    return {
        "solar_bands": _solar_bands(solar),
        "thermal_bands": _thermal_bands(thermal),
    }


def _sample(sample_id="SCA-01", scans=None):
    return {
        "id": sample_id,
        "scans": scans if scans is not None else [_scan(), _scan()],
    }


def _spec(**overrides):
    spec = {
        "designated_ids": ["SCA-01", "SCA-02"],
        "samples": [_sample("SCA-01"), _sample("SCA-02")],
        "instruments": dict(INSTRUMENTS),
    }
    spec.update(overrides)
    return spec


class WeightedReductionTests(unittest.TestCase):
    def test_uniform_reflectance_reduces_to_itself(self):
        self.assertAlmostEqual(weighted_reflectance(_solar_bands(0.10)), 0.10, places=9)

    def test_weights_carry_the_spectrum(self):
        bands = [
            {"wavelength_um": 0.5, "weight": 3.0, "reflectance": 0.20},
            {"wavelength_um": 1.0, "weight": 1.0, "reflectance": 0.40},
        ]
        self.assertAlmostEqual(weighted_reflectance(bands), 0.25, places=9)

    def test_absorptance_is_one_minus_weighted_reflectance(self):
        self.assertAlmostEqual(solar_absorptance(_solar_bands(0.10)), 0.90, places=9)

    def test_emittance_is_one_minus_weighted_reflectance(self):
        self.assertAlmostEqual(
            hemispherical_emittance(_thermal_bands(0.15)), 0.85, places=9
        )

    def test_reflectance_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            weighted_reflectance(_solar_bands(1.4))

    def test_negative_reflectance_is_rejected(self):
        with self.assertRaises(ValueError):
            weighted_reflectance(_solar_bands(-0.01))

    def test_zero_weight_band_is_rejected(self):
        with self.assertRaises(ValueError):
            weighted_reflectance(
                [{"wavelength_um": 0.5, "weight": 0.0, "reflectance": 0.1}]
            )

    def test_empty_band_set_is_rejected(self):
        with self.assertRaises(ValueError):
            weighted_reflectance([])


class RatioAndSpreadTests(unittest.TestCase):
    def test_ratio_is_absorptance_over_emittance(self):
        self.assertAlmostEqual(
            absorptance_emittance_ratio(0.90, 0.45), 2.0, places=9
        )

    def test_zero_emittance_is_rejected(self):
        with self.assertRaises(ValueError):
            absorptance_emittance_ratio(0.90, 0.0)

    def test_mean_of_repeat_readings(self):
        self.assertAlmostEqual(mean_value([0.90, 0.88]), 0.89, places=9)

    def test_spread_is_the_full_range(self):
        self.assertAlmostEqual(reading_spread([0.90, 0.88, 0.89]), 0.02, places=9)

    def test_spread_of_a_single_reading_is_zero(self):
        self.assertAlmostEqual(reading_spread([0.90]), 0.0, places=9)


class InstrumentRangeTests(unittest.TestCase):
    def test_bands_inside_the_range_are_all_covered(self):
        self.assertEqual(uncovered_wavelengths_um(_solar_bands(), (0.25, 2.5)), [])

    def test_band_beyond_the_range_is_reported(self):
        self.assertEqual(
            uncovered_wavelengths_um(_thermal_bands(), (0.25, 2.5)), [5.0, 10.0]
        )

    def test_band_exactly_on_the_range_edge_is_covered(self):
        bands = [{"wavelength_um": 2.5, "weight": 1.0, "reflectance": 0.1}]
        self.assertEqual(uncovered_wavelengths_um(bands, (0.25, 2.5)), [])

    def test_inverted_instrument_range_is_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_wavelengths_um(_solar_bands(), (2.5, 0.25))


class SubgroupCoverageTests(unittest.TestCase):
    def test_full_coverage_leaves_nothing_missing(self):
        coverage = resolve_subgroup(["A", "B"], ["A", "B"])
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(coverage["extra"], [])
        self.assertEqual(coverage["covered"], ["A", "B"])

    def test_unmeasured_designated_sample_is_missing(self):
        coverage = resolve_subgroup(["A", "B"], ["A"])
        self.assertEqual(coverage["missing"], ["B"])

    def test_undesignated_measured_sample_is_extra(self):
        coverage = resolve_subgroup(["A"], ["A", "Z"])
        self.assertEqual(coverage["extra"], ["Z"])

    def test_duplicate_designated_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_subgroup(["A", "A"], ["A"])

    def test_empty_designated_subgroup_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_subgroup([], ["A"])


class SampleEvaluationTests(unittest.TestCase):
    def test_repeatable_sample_conforms(self):
        record = evaluate_sample(_sample(), INSTRUMENTS)
        self.assertTrue(record["conforms"])
        self.assertAlmostEqual(record["solar_absorptance"], 0.90, places=9)
        self.assertAlmostEqual(record["hemispherical_emittance"], 0.85, places=9)

    def test_ratio_is_carried_on_the_record(self):
        record = evaluate_sample(_sample(), INSTRUMENTS)
        self.assertAlmostEqual(
            record["absorptance_emittance_ratio"], 0.90 / 0.85, places=9
        )

    def test_spread_exactly_on_the_repeatability_limit_is_accepted(self):
        scans = [_scan(solar=0.10), _scan(solar=0.10 + DEFAULT_ABSORPTANCE_REPEATABILITY)]
        record = evaluate_sample(_sample(scans=scans), INSTRUMENTS)
        self.assertAlmostEqual(
            record["absorptance_spread"], DEFAULT_ABSORPTANCE_REPEATABILITY, places=9
        )
        self.assertTrue(record["conforms"])

    def test_scatter_beyond_the_limit_is_a_finding(self):
        scans = [_scan(solar=0.10), _scan(solar=0.25)]
        record = evaluate_sample(_sample(scans=scans), INSTRUMENTS)
        self.assertFalse(record["conforms"])
        self.assertFalse(record["repeatable"])

    def test_single_scan_cannot_show_repeatability(self):
        record = evaluate_sample(_sample(scans=[_scan()]), INSTRUMENTS)
        self.assertEqual(record["scan_count"], 1)
        self.assertLess(record["scan_count"], DEFAULT_REQUIRED_SCANS)
        self.assertFalse(record["conforms"])

    def test_band_outside_the_instrument_range_is_a_finding(self):
        scans = [
            {"solar_bands": _thermal_bands(), "thermal_bands": _thermal_bands()},
            {"solar_bands": _thermal_bands(), "thermal_bands": _thermal_bands()},
        ]
        record = evaluate_sample(_sample(scans=scans), INSTRUMENTS)
        self.assertTrue(record["bands_out_of_instrument_range"])
        self.assertFalse(record["conforms"])

    def test_sample_without_scans_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample(_sample(scans=[]), INSTRUMENTS)

    def test_scan_without_thermal_bands_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample(
                _sample(scans=[{"solar_bands": _solar_bands(), "thermal_bands": []}]),
                INSTRUMENTS,
            )

    def test_empty_sample_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample(_sample(sample_id="  "), INSTRUMENTS)


class MeasurementAssessmentTests(unittest.TestCase):
    def test_complete_subgroup_is_valid(self):
        result = assess_thermo_optical_measurement(_spec())
        self.assertTrue(result["valid"])
        self.assertEqual(result["samples_measured"], 2)
        self.assertEqual(result["subgroup_size"], 2)
        self.assertAlmostEqual(result["mean_solar_absorptance"], 0.90, places=9)

    def test_designated_sample_never_measured_is_reported(self):
        result = assess_thermo_optical_measurement(
            _spec(designated_ids=["SCA-01", "SCA-02", "SCA-03"])
        )
        self.assertEqual(result["coverage"]["missing"], ["SCA-03"])
        self.assertFalse(result["valid"])

    def test_sample_outside_the_subgroup_is_reported(self):
        result = assess_thermo_optical_measurement(
            _spec(samples=[_sample("SCA-01"), _sample("SCA-02"), _sample("SCA-99")])
        )
        self.assertEqual(result["coverage"]["extra"], ["SCA-99"])
        self.assertFalse(result["valid"])

    def test_declared_limits_override_the_defaults(self):
        scans = [_scan(solar=0.10), _scan(solar=0.14)]
        spec = _spec(
            samples=[_sample("SCA-01", scans), _sample("SCA-02")],
            limits={"absorptance_repeatability": 0.05},
        )
        self.assertTrue(assess_thermo_optical_measurement(spec)["valid"])

    def test_empty_sample_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermo_optical_measurement(_spec(samples=[]))

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermo_optical_measurement(["designated_ids"])

    def test_missing_instruments_block_is_rejected(self):
        spec = _spec()
        del spec["instruments"]
        with self.assertRaises(ValueError):
            assess_thermo_optical_measurement(spec)


if __name__ == "__main__":
    unittest.main()
