"""Contract tests for the ECSS-Q-ST-70-29 concentration-determination logic."""

import unittest

from q7029_concentration_determination_logic import (
    STATE_BELOW_QUANTITATION,
    STATE_NON_DETECTED,
    STATE_QUANTIFIED,
    blank_corrected_area,
    determine_compound,
    determine_concentrations,
    mass_from_area,
    mass_per_cubic_metre,
    mass_per_gram,
    quantitation_state,
    recovery_corrected_mass,
    validate_calibration,
    validate_run_conditions,
)

# Linear-in-the-working-range calibration: area 1000 counts per microgram.
CAL = [(1000.0, 1.0), (10000.0, 10.0), (100000.0, 100.0)]

CONDITIONS = validate_run_conditions(50.0, 0.002, 0.8, 72.0)


def entry(compound, sample_area, blank_area=0.0, loq=1.0, lod=0.3):
    return {
        "compound": compound,
        "sample_area": sample_area,
        "blank_area": blank_area,
        "calibration": CAL,
        "loq_ug": loq,
        "lod_ug": lod,
    }


class RunConditionTests(unittest.TestCase):
    def test_valid_conditions_are_normalised(self):
        cond = validate_run_conditions(50.0, 0.002, 0.8)
        self.assertAlmostEqual(cond["sample_mass_g"], 50.0)
        self.assertAlmostEqual(cond["vessel_volume_m3"], 0.002)
        self.assertAlmostEqual(cond["recovery_fraction"], 0.8)

    def test_full_recovery_is_allowed(self):
        self.assertAlmostEqual(
            validate_run_conditions(50.0, 0.002, 1.0)["recovery_fraction"], 1.0, places=9
        )

    def test_zero_sample_mass_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_conditions(0.0, 0.002, 0.8)

    def test_recovery_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_conditions(50.0, 0.002, 1.4)

    def test_zero_recovery_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_conditions(50.0, 0.002, 0.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_conditions(50.0, 0.002, 0.8, -72.0)

    def test_boolean_volume_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_conditions(50.0, True, 0.8)


class CalibrationTests(unittest.TestCase):
    def test_valid_series_is_returned(self):
        self.assertEqual(len(validate_calibration(CAL)), 3)

    def test_single_point_series_rejected(self):
        with self.assertRaises(ValueError):
            validate_calibration([(1000.0, 1.0)])

    def test_non_monotone_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_calibration([(1000.0, 1.0), (1000.0, 2.0)])

    def test_non_monotone_mass_rejected(self):
        with self.assertRaises(ValueError):
            validate_calibration([(1000.0, 5.0), (2000.0, 5.0)])

    def test_mass_at_a_tabulated_point(self):
        self.assertAlmostEqual(mass_from_area(10000.0, CAL), 10.0, places=9)

    def test_mass_interpolated_between_points(self):
        self.assertAlmostEqual(mass_from_area(5500.0, CAL), 5.5, places=9)

    def test_area_below_the_span_refused(self):
        with self.assertRaises(ValueError):
            mass_from_area(500.0, CAL)

    def test_area_above_the_span_refused(self):
        with self.assertRaises(ValueError):
            mass_from_area(200000.0, CAL)


class BlankAndRecoveryTests(unittest.TestCase):
    def test_blank_is_subtracted_before_calibration(self):
        self.assertAlmostEqual(blank_corrected_area(5000.0, 1000.0), 4000.0, places=9)

    def test_sample_at_the_blank_is_a_non_detection(self):
        self.assertAlmostEqual(blank_corrected_area(1000.0, 1000.0), 0.0, places=9)

    def test_sample_below_the_blank_does_not_go_negative(self):
        self.assertAlmostEqual(blank_corrected_area(800.0, 1000.0), 0.0, places=9)

    def test_negative_blank_rejected(self):
        with self.assertRaises(ValueError):
            blank_corrected_area(5000.0, -10.0)

    def test_recovery_correction_raises_the_mass(self):
        self.assertAlmostEqual(recovery_corrected_mass(8.0, 0.8), 10.0, places=9)

    def test_full_recovery_leaves_the_mass_unchanged(self):
        self.assertAlmostEqual(recovery_corrected_mass(8.0, 1.0), 8.0, places=9)

    def test_recovery_outside_the_interval_rejected(self):
        with self.assertRaises(ValueError):
            recovery_corrected_mass(8.0, 0.0)


class QuantitationStateTests(unittest.TestCase):
    def test_mass_above_the_quantitation_limit(self):
        self.assertEqual(quantitation_state(5.0, 1.0, 0.3), STATE_QUANTIFIED)

    def test_mass_exactly_on_the_quantitation_limit_is_quantified(self):
        self.assertEqual(quantitation_state(1.0, 1.0, 0.3), STATE_QUANTIFIED)

    def test_mass_between_the_limits_is_below_quantitation(self):
        self.assertEqual(quantitation_state(0.5, 1.0, 0.3), STATE_BELOW_QUANTITATION)

    def test_mass_exactly_on_the_detection_limit_is_below_quantitation(self):
        self.assertEqual(quantitation_state(0.3, 1.0, 0.3), STATE_BELOW_QUANTITATION)

    def test_mass_under_the_detection_limit_is_non_detected(self):
        self.assertEqual(quantitation_state(0.1, 1.0, 0.3), STATE_NON_DETECTED)

    def test_detection_limit_above_quantitation_limit_rejected(self):
        with self.assertRaises(ValueError):
            quantitation_state(0.5, 0.3, 1.0)


class NormalisationTests(unittest.TestCase):
    def test_micrograms_per_gram(self):
        self.assertAlmostEqual(mass_per_gram(100.0, 50.0), 2.0, places=9)

    def test_milligrams_per_cubic_metre(self):
        self.assertAlmostEqual(mass_per_cubic_metre(100.0, 0.002), 50.0, places=9)

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            mass_per_cubic_metre(100.0, 0.0)


class CompoundRecordTests(unittest.TestCase):
    def test_quantified_record_carries_both_normalisations(self):
        record = determine_compound(entry("toluene", 9000.0, 1000.0), CONDITIONS)
        self.assertEqual(record["state"], STATE_QUANTIFIED)
        self.assertAlmostEqual(record["recovered_mass_ug"], 8.0, places=9)
        self.assertAlmostEqual(record["released_mass_ug"], 10.0, places=9)
        self.assertAlmostEqual(record["ug_per_g"], 0.2, places=9)
        self.assertAlmostEqual(record["mg_per_m3"], 5.0, places=9)

    def test_non_detection_reports_zero_mass_with_a_note(self):
        record = determine_compound(entry("benzene", 900.0, 1000.0), CONDITIONS)
        self.assertEqual(record["state"], STATE_NON_DETECTED)
        self.assertAlmostEqual(record["reported_mass_ug"], 0.0, places=9)
        self.assertEqual(len(record["notes"]), 1)

    def test_below_quantitation_is_reported_at_the_limit_not_zero(self):
        record = determine_compound(
            entry("hexanal", 2000.0, 1000.0, loq=2.0, lod=0.5), CONDITIONS
        )
        self.assertEqual(record["state"], STATE_BELOW_QUANTITATION)
        self.assertAlmostEqual(record["released_mass_ug"], 1.25, places=9)
        self.assertAlmostEqual(record["reported_mass_ug"], 2.0, places=9)

    def test_entry_missing_a_limit_rejected(self):
        bad = entry("toluene", 9000.0)
        del bad["loq_ug"]
        with self.assertRaises(ValueError):
            determine_compound(bad, CONDITIONS)

    def test_over_range_response_is_refused(self):
        with self.assertRaises(ValueError):
            determine_compound(entry("toluene", 400000.0), CONDITIONS)


class DetermineConcentrationsTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "entries": [
                entry("toluene", 9000.0, 1000.0),
                entry("hexanal", 21000.0, 1000.0),
            ],
            "sample_mass_g": 50.0,
            "vessel_volume_m3": 0.002,
            "recovery_fraction": 0.8,
        }
        spec.update(overrides)
        return spec

    def test_totals_are_the_sum_of_the_reported_masses(self):
        result = determine_concentrations(self._spec())
        self.assertAlmostEqual(result["total_reported_mass_ug"], 35.0, places=9)
        self.assertEqual(result["quantified_count"], 2)

    def test_total_normalisations_agree_with_the_totals(self):
        result = determine_concentrations(self._spec())
        self.assertAlmostEqual(result["total_ug_per_g"], 0.7, places=9)
        self.assertAlmostEqual(result["total_mg_per_m3"], 17.5, places=9)

    def test_clean_run_has_no_findings(self):
        self.assertEqual(determine_concentrations(self._spec())["findings"], [])

    def test_non_detection_raises_a_finding(self):
        spec = self._spec(entries=[entry("toluene", 9000.0, 1000.0), entry("benzene", 900.0, 1000.0)])
        result = determine_concentrations(spec)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("benzene", result["findings"][0])

    def test_duplicate_compound_rejected(self):
        spec = self._spec(entries=[entry("toluene", 9000.0, 1000.0), entry("toluene", 21000.0, 1000.0)])
        with self.assertRaises(ValueError):
            determine_concentrations(spec)

    def test_empty_entry_list_rejected(self):
        with self.assertRaises(ValueError):
            determine_concentrations(self._spec(entries=[]))

    def test_missing_required_key_rejected(self):
        spec = self._spec()
        del spec["vessel_volume_m3"]
        with self.assertRaises(ValueError):
            determine_concentrations(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            determine_concentrations(["entries"])

    def test_lower_recovery_raises_the_released_mass(self):
        high = determine_concentrations(self._spec(recovery_fraction=0.8))
        low = determine_concentrations(self._spec(recovery_fraction=0.4))
        self.assertAlmostEqual(
            low["total_reported_mass_ug"], 2.0 * high["total_reported_mass_ug"], places=9
        )


if __name__ == "__main__":
    unittest.main()
